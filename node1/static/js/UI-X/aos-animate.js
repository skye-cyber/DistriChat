import './aos/aos.css';
import AOS from 'aos';

window.onload = function() {
    AOS.init({
        once: false,
        mirror: true,
        duration: 700,
        startEvent: 'DOMContentLoaded',
    });

    setTimeout(() => {
        AOS.refresh();
    }, 300);
}
