// Acceler8-ai Landing Page Interactions

// Smooth scroll behavior for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      target.scrollIntoView({ behavior: 'smooth' });
    }
  });
});

// Intersection Observer for scroll-triggered animations
const observerOptions = {
  threshold: 0.1,
  rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('in-view');
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

// Observe all scroll-triggered elements
document.querySelectorAll('.scroll-fade-in, .scroll-slide-left, .scroll-slide-right').forEach(el => {
  observer.observe(el);
});

// Stagger animations for card grids
function setupStaggerAnimations() {
  document.querySelectorAll('.stagger-children').forEach(container => {
    const cards = container.querySelectorAll(':scope > *');
    cards.forEach((card, index) => {
      card.style.opacity = '0';
      card.style.transform = 'translateY(30px)';
      card.style.animation = `none`;

      // Trigger animation when element enters view
      const cardObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            setTimeout(() => {
              entry.target.style.animation = `fadeInUp 0.6s ease-out forwards`;
            }, index * 100);
            cardObserver.unobserve(entry.target);
          }
        });
      }, observerOptions);

      cardObserver.observe(card);
    });
  });
}

setupStaggerAnimations();

// Active navigation link highlighting
function updateActiveNavLink() {
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-menu a');

  window.addEventListener('scroll', () => {
    let currentSection = '';

    sections.forEach(section => {
      const sectionTop = section.offsetTop;
      if (scrollY >= sectionTop - 200) {
        currentSection = section.getAttribute('id');
      }
    });

    navLinks.forEach(link => {
      link.classList.remove('active');
      if (link.getAttribute('href') === `#${currentSection}`) {
        link.classList.add('active');
      }
    });
  });
}

updateActiveNavLink();

// Button click handlers
document.querySelectorAll('.btn-primary, .btn-secondary, .nav-cta').forEach(btn => {
  btn.addEventListener('click', function() {
    // Scroll to fit-review section
    const fitReviewSection = document.getElementById('fit-review');
    if (fitReviewSection && (this.textContent.includes('Technology Fit Review') || this.textContent.includes('Start'))) {
      fitReviewSection.scrollIntoView({ behavior: 'smooth' });
    }
  });
});

// Prevent layout shift on page load
window.addEventListener('load', () => {
  document.body.style.overflowX = 'hidden';
});

// Handle navigation on small screens
const navMenu = document.querySelector('.nav-menu');
const navLinks = document.querySelectorAll('.nav-menu a');

navLinks.forEach(link => {
  link.addEventListener('click', () => {
    // Close mobile menu if open (for future mobile menu implementation)
  });
});

// Accessibility: focus visible on keyboard navigation
document.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    document.body.classList.add('keyboard-nav');
  }
});

document.addEventListener('mousedown', () => {
  document.body.classList.remove('keyboard-nav');
});

console.log('Acceler8-ai landing page interactions loaded');
