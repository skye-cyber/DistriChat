## 🛠️ Local Development Setup

### 1. **Project Structure for Multiple Nodes**

```
districhat/
├── central_server/          # Main central server
│   ├── manage.py
│   ├── districhat/
│   └── [all your apps]
├── node1/                   # First node instance
│   ├── manage.py
│   └── [same apps, different config]
├── node2/                   # Second node instance  
│   ├── manage.py
│   └── [same apps, different config]
└── shared_settings.py       # Common settings
```

### 2. **Shared Settings (shared_settings.py)**

```python
"""
Shared settings for all nodes and central server.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Common settings
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'users',
    'chat',
    'nodes',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'districhat.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Database - use SQLite for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'users.CustomUser'

# Channel layers for WebSockets
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

### 3. **Central Server Settings (central_server/districhat/settings.py)**

```python
from shared_settings import *

# Central server specific settings
DEBUG = True
SECRET_KEY = 'central-server-secret-key-change-in-production'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'central.chatserver.local']

# Central server runs on port 8000
PORT = 8000

# Database for central server
DATABASES['default']['NAME'] = BASE_DIR / 'central_db.sqlite3'

# Central server specific apps (if any)
INSTALLED_APPS += [
    # Add central-server specific apps here
]

# Central server is the main WSGI application
WSGI_APPLICATION = 'districhat.wsgi.application'
ASGI_APPLICATION = 'districhat.asgi.application'

# Login URLs
LOGIN_REDIRECT_URL = 'chat:dashboard'
LOGIN_URL = 'users:login'
LOGOUT_REDIRECT_URL = 'index'

# Central server URL
CENTRAL_SERVER_URL = 'http://localhost:8000'
```

### 4. **Node 1 Settings (node1/districhat/settings.py)**

```python
from shared_settings import *

# Node 1 specific settings
DEBUG = True
SECRET_KEY = 'node1-secret-key-change-in-production'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'node1.chatserver.local']

# Node 1 runs on port 8001
PORT = 8001

# Database for node 1
DATABASES['default']['NAME'] = BASE_DIR / 'node1_db.sqlite3'

# Node settings
NODE_NAME = 'Local-Node-1'
NODE_URL = 'http://localhost:8001'
MAX_ROOMS = 50

# This is a node, not the central server
IS_NODE = True
CENTRAL_SERVER_URL = 'http://localhost:8000'  # Points to central server

# Node-specific middleware
MIDDLEWARE += [
    'nodes.middleware.NodeMiddleware',
]
```

### 5. **Node 2 Settings (node2/districhat/settings.py)**

```python
from shared_settings import *

# Node 2 specific settings
DEBUG = True
SECRET_KEY = 'node2-secret-key-change-in-production'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'node2.chatserver.local']

# Node 2 runs on port 8002
PORT = 8002

# Database for node 2
DATABASES['default']['NAME'] = BASE_DIR / 'node2_db.sqlite3'

# Node settings
NODE_NAME = 'Local-Node-2'
NODE_URL = 'http://localhost:8002'
MAX_ROOMS = 50

# This is a node, not the central server
IS_NODE = True
CENTRAL_SERVER_URL = 'http://localhost:8000'  # Points to central server

# Node-specific middleware
MIDDLEWARE += [
    'nodes.middleware.NodeMiddleware',
]
```

### 6. **Node Middleware (nodes/middleware.py)**

```python
import requests
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class NodeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # If this is a node, register with central server on startup
        if hasattr(settings, 'IS_NODE') and settings.IS_NODE:
            self.register_with_central_server()
            
        response = self.get_response(request)
        return response
    
    def register_with_central_server(self):
        """Register this node with the central server."""
        try:
            # Check if we're already registered
            from .models import Node
            if Node.objects.filter(url=settings.NODE_URL).exists():
                return
                
            # Register with central server
            registration_data = {
                'node_name': settings.NODE_NAME,
                'node_url': settings.NODE_URL,
                'admin_email': 'admin@chatserver.local',
                'description': f'Local development node - {settings.NODE_NAME}',
                'max_rooms_capacity': settings.MAX_ROOMS
            }
            
            response = requests.post(
                f'{settings.CENTRAL_SERVER_URL}/nodes/register/',
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Node {settings.NODE_NAME} registered with central server")
                
                # Auto-approve for development
                registration_id = response.json().get('registration_id')
                if registration_id:
                    self.auto_approve_node(registration_id)
            else:
                logger.error(f"Failed to register node: {response.text}")
                
        except Exception as e:
            logger.error(f"Node registration error: {e}")
    
    def auto_approve_node(self, registration_id):
        """Auto-approve this node for development."""
        try:
            # In production, this would require admin approval
            # For development, we auto-approve
            from .models import Node
            
            # Create node directly since we're in development
            node = Node.objects.create(
                name=settings.NODE_NAME,
                url=settings.NODE_URL,
                max_rooms=settings.MAX_ROOMS,
                status='online'
            )
            logger.info(f"Node {node.name} auto-approved for development")
            
        except Exception as e:
            logger.error(f"Auto-approval error: {e}")
```

### 7. **Node Heartbeat Service (nodes/services.py)**

```python
import requests
import threading
import time
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class HeartbeatService:
    def __init__(self):
        self.is_running = False
        self.thread = None
        
    def start(self):
        """Start the heartbeat service."""
        if self.is_running:
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()
        logger.info("Heartbeat service started")
        
    def stop(self):
        """Stop the heartbeat service."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Heartbeat service stopped")
        
    def _heartbeat_loop(self):
        """Main heartbeat loop."""
        while self.is_running:
            try:
                self.send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            
            # Wait 30 seconds before next heartbeat
            time.sleep(30)
    
    def send_heartbeat(self):
        """Send heartbeat to central server."""
        try:
            from .models import Node
            from chat.models import ChatRoom
            
            node = Node.objects.filter(url=settings.NODE_URL).first()
            if not node:
                logger.error("Node not found for heartbeat")
                return
                
            # Calculate current load
            active_rooms = ChatRoom.objects.filter(node=node, is_active=True).count()
            load_percentage = (active_rooms / node.max_rooms) * 100 if node.max_rooms > 0 else 0
            
            heartbeat_data = {
                'load': load_percentage,
                'active_connections': 0,  # You'd track WebSocket connections
                'active_rooms': active_rooms,
                'memory_usage': 0,  # You'd get this from system monitoring
                'cpu_usage': 0      # You'd get this from system monitoring
            }
            
            response = requests.post(
                f'{settings.CENTRAL_SERVER_URL}/nodes/heartbeat/{node.id}/',
                json=heartbeat_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug(f"Heartbeat sent successfully - Load: {load_percentage:.1f}%")
            else:
                logger.error(f"Heartbeat failed: {response.text}")
                
        except Exception as e:
            logger.error(f"Heartbeat send error: {e}")

# Global heartbeat service instance
heartbeat_service = HeartbeatService()
```

### 8. **Node App Config (nodes/apps.py)**

```python
from django.apps import AppConfig

class NodesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nodes'
    
    def ready(self):
        """Start heartbeat service when app is ready."""
        from django.conf import settings
        
        # Only start heartbeat if this is a node (not central server)
        if hasattr(settings, 'IS_NODE') and settings.IS_NODE:
            from .services import heartbeat_service
            heartbeat_service.start()
```

### 9. **Setup Script (setup_local_nodes.py)**

```python
#!/usr/bin/env python3
"""
Setup script for local development nodes.
"""
import os
import sys
import subprocess
import time

def run_command(cmd, cwd=None):
    """Run a shell command."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.returncode == 0

def setup_central_server():
    """Setup central server."""
    print("\n🔧 Setting up Central Server...")
    
    # Create migrations
    if not run_command("python manage.py makemigrations", "central_server"):
        return False
        
    # Run migrations
    if not run_command("python manage.py migrate", "central_server"):
        return False
        
    # Create superuser
    print("\n👤 Create superuser for central server:")
    run_command("python manage.py createsuperuser", "central_server")
    
    return True

def setup_node(node_dir, node_name):
    """Setup a node."""
    print(f"\n🔧 Setting up {node_name}...")
    
    # Create migrations
    if not run_command("python manage.py makemigrations", node_dir):
        return False
        
    # Run migrations
    if not run_command("python manage.py migrate", node_dir):
        return False
        
    return True

def main():
    """Main setup function."""
    print("🚀 Setting up DistriChat Local Development Environment")
    print("=" * 50)
    
    # Check if Redis is running (required for channels)
    print("\n🔍 Checking Redis...")
    if not run_command("redis-cli ping"):
        print("❌ Redis is not running. Please start Redis:")
        print("   On macOS: brew services start redis")
        print("   On Ubuntu: sudo systemctl start redis")
        print("   On Windows: redis-server")
        return
    
    print("✅ Redis is running")
    
    # Setup central server
    if not setup_central_server():
        print("❌ Failed to setup central server")
        return
        
    # Setup nodes
    nodes = [
        ("node1", "Local Node 1"),
        ("node2", "Local Node 2")
    ]
    
    for node_dir, node_name in nodes:
        if not setup_node(node_dir, node_name):
            print(f"❌ Failed to setup {node_name}")
            return
    
    print("\n✅ Setup completed successfully!")
    print("\n🎯 Next steps:")
    print("1. Start Redis: redis-server")
    print("2. Start Central Server: cd central_server && python manage.py runserver 8000")
    print("3. Start Node 1: cd node1 && python manage.py runserver 8001") 
    print("4. Start Node 2: cd node2 && python manage.py runserver 8002")
    print("5. Access Central Server: http://localhost:8000")
    print("6. Access Node 1: http://localhost:8001")
    print("7. Access Node 2: http://localhost:8002")

if __name__ == "__main__":
    main()
```

### 10. **Startup Script (start_all.py)**

```python
#!/usr/bin/env python3
"""
Start all servers for local development.
"""
import subprocess
import time
import sys
import os

def start_server(name, command, cwd):
    """Start a server in a new process."""
    print(f"🚀 Starting {name}...")
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"✅ {name} started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None

def main():
    """Main startup function."""
    print("🎪 Starting DistriChat Local Development Environment")
    print("=" * 50)
    
    processes = []
    
    try:
        # Start central server
        central_process = start_server(
            "Central Server", 
            "python manage.py runserver 8000",
            "central_server"
        )
        if central_process:
            processes.append(("Central Server", central_process))
        
        time.sleep(3)  # Wait for central server to start
        
        # Start nodes
        nodes = [
            ("Node 1", "node1", "python manage.py runserver 8001"),
            ("Node 2", "node2", "python manage.py runserver 8002")
        ]
        
        for name, directory, command in nodes:
            process = start_server(name, command, directory)
            if process:
                processes.append((name, process))
            time.sleep(2)  # Stagger node startup
        
        print("\n✅ All servers started!")
        print("\n🌐 Access Points:")
        print("   Central Server: http://localhost:8000")
        print("   Node 1:         http://localhost:8001") 
        print("   Node 2:         http://localhost:8002")
        print("\n⏹️  Press Ctrl+C to stop all servers")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping all servers...")
        for name, process in processes:
            print(f"⏹️  Stopping {name}...")
            process.terminate()
            process.wait()
        print("✅ All servers stopped")

if __name__ == "__main__":
    main()
```

## 🚀 Quick Start

### 1. **Create the directory structure:**
```bash
mkdir -p central_server/node1 node2
# Copy your existing project files to each directory
```

### 2. **Run the setup:**
```bash
python setup_local_nodes.py
```

### 3. **Start everything:**
```bash
python start_all.py
```

## 🎯 What This Gives You:

### **Central Server (port 8000)**
- Main dashboard for node management
- User authentication and registration
- Load balancing across nodes
- System monitoring

### **Node 1 (port 8001) & Node 2 (port 8002)**
- Host actual chat rooms
- Handle real-time WebSocket connections
- Report health to central server
- Auto-register with central system

### **Key Features:**
- ✅ **Auto-registration** - Nodes automatically register with central server
- ✅ **Heartbeat monitoring** - Nodes report health every 30 seconds
- ✅ **Load balancing** - New rooms assigned to least loaded node
- ✅ **Development-friendly** - Easy to start/stop all services
- ✅ **Separate databases** - Each instance has its own SQLite database
