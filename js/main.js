/**
 * Strong Trendz - Main JavaScript File
 * Contains all interactive functionality for the website
 */

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize navigation
    initNavigation();
    
    // Setup form validation if forms exist
    setupFormValidation();
    
    // Initialize modals if they exist
    initModals();
    
    // Add fade-in animation to content
    document.querySelector('.content')?.classList.add('fade-in');
});

/**
 * Initialize navigation functionality
 */
function initNavigation() {
    // Highlight current page in navigation
    highlightCurrentPage();
    
    // Add click events to navigation links
    const navLinks = document.querySelectorAll('.sidebar-nav a');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // If it's a dropdown, prevent default and toggle dropdown
            if (this.classList.contains('dropdown-toggle')) {
                e.preventDefault();
                this.nextElementSibling?.classList.toggle('show');
            }
        });
    });
}

/**
 * Highlight the current page in navigation
 */
function highlightCurrentPage() {
    // Get the current page filename
    const path = window.location.pathname;
    const page = path.split("/").pop();
    
    // Get all navigation links
    const navLinks = document.querySelectorAll('.sidebar-nav a');
    
    // Reset active class
    navLinks.forEach(link => link.classList.remove('active'));
    
    // Add active class to current page link
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        
        // Check if this link matches the current page
        if (href === page || 
            (page === '' && href === 'index.html') || 
            (page === 'index.html' && href === './')) {
            link.classList.add('active');
        }
    });
}

/**
 * Setup form validation for all forms
 */
function setupFormValidation() {
    // Get all forms on the page
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Prevent default form submission
            e.preventDefault();
            
            // Check if form is valid
            if (validateForm(this)) {
                // Show success message
                showMessage('Form submitted successfully!', 'success');
                
                // Reset form
                this.reset();
                
                // In a real implementation, you would submit the form data to a server here
                console.log('Form would be submitted to server');
            }
        });
    });
}

/**
 * Validate form inputs
 * @param {HTMLFormElement} form - The form to validate
 * @returns {boolean} - Whether the form is valid
 */
function validateForm(form) {
    let isValid = true;
    
    // Get all required inputs
    const requiredInputs = form.querySelectorAll('[required]');
    
    // Check each required input
    requiredInputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('error');
            
            // Add error message
            const errorMsg = document.createElement('div');
            errorMsg.className = 'error-message';
            errorMsg.textContent = 'This field is required';
            
            // Remove any existing error message
            const existingError = input.parentNode.querySelector('.error-message');
            if (existingError) {
                existingError.remove();
            }
            
            // Add new error message
            input.parentNode.appendChild(errorMsg);
        } else {
            input.classList.remove('error');
            const existingError = input.parentNode.querySelector('.error-message');
            if (existingError) {
                existingError.remove();
            }
        }
    });
    
    // Validate email field if exists
    const emailInput = form.querySelector('input[type="email"]');
    if (emailInput && emailInput.value.trim()) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(emailInput.value.trim())) {
            isValid = false;
            emailInput.classList.add('error');
            
            // Add error message
            const errorMsg = document.createElement('div');
            errorMsg.className = 'error-message';
            errorMsg.textContent = 'Please enter a valid email address';
            
            // Remove any existing error message
            const existingError = emailInput.parentNode.querySelector('.error-message');
            if (existingError) {
                existingError.remove();
            }
            
            // Add new error message
            emailInput.parentNode.appendChild(errorMsg);
        }
    }
    
    // Validate phone field if exists
    const phoneInput = form.querySelector('input[type="tel"]');
    if (phoneInput && phoneInput.value.trim()) {
        const phonePattern = /^\d{10,}$/;
        if (!phonePattern.test(phoneInput.value.replace(/\D/g, ''))) {
            isValid = false;
            phoneInput.classList.add('error');
            
            // Add error message
            const errorMsg = document.createElement('div');
            errorMsg.className = 'error-message';
            errorMsg.textContent = 'Please enter a valid phone number';
            
            // Remove any existing error message
            const existingError = phoneInput.parentNode.querySelector('.error-message');
            if (existingError) {
                existingError.remove();
            }
            
            // Add new error message
            phoneInput.parentNode.appendChild(errorMsg);
        }
    }
    
    return isValid;
}

/**
 * Display a message to the user
 * @param {string} message - The message to display
 * @param {string} type - The type of message (success, error, info)
 */
function showMessage(message, type = 'info') {
    // Create message element
    const messageEl = document.createElement('div');
    messageEl.className = `message message-${type}`;
    messageEl.textContent = message;
    
    // Add to document
    document.body.appendChild(messageEl);
    
    // Show message
    setTimeout(() => {
        messageEl.classList.add('show');
    }, 10);
    
    // Remove message after delay
    setTimeout(() => {
        messageEl.classList.remove('show');
        setTimeout(() => {
            messageEl.remove();
        }, 300);
    }, 3000);
}

/**
 * Initialize modal dialogs
 */
function initModals() {
    // Get all modal triggers
    const modalTriggers = document.querySelectorAll('[data-toggle="modal"]');
    
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get target modal
            const targetId = this.getAttribute('data-target');
            const modal = document.querySelector(targetId);
            
            if (modal) {
                // Show modal
                modal.style.display = 'flex';
                
                // Get close button
                const closeBtn = modal.querySelector('.modal-close');
                if (closeBtn) {
                    closeBtn.addEventListener('click', function() {
                        modal.style.display = 'none';
                    });
                }
                
                // Close when clicking outside
                modal.addEventListener('click', function(e) {
                    if (e.target === modal) {
                        modal.style.display = 'none';
                    }
                });
            }
        });
    });
}

/**
 * Create a stock chart
 * @param {string} containerId - The ID of the container element
 */
function createStockChart(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Check if the chart library is loaded
    if (typeof Chart === 'undefined') {
        console.error('Chart.js library is not loaded');
        return;
    }
    
    // Create canvas for chart
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);
    
    // Sample data
    const data = {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        datasets: [{
            label: 'Stock Price',
            data: [10, 12, 11, 14, 16, 15, 14, 16, 18, 20, 22, 24],
            borderColor: '#0486c2',
            backgroundColor: 'rgba(4, 134, 194, 0.1)',
            tension: 0.4,
            fill: true
        }]
    };
    
    // Chart configuration
    const config = {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    };
    
    // Create chart
    new Chart(canvas, config);
}

/**
 * Load content dynamically via AJAX
 * @param {string} url - The URL to load
 * @param {string} targetId - The ID of the element to load content into
 */
function loadContent(url, targetId) {
    const target = document.getElementById(targetId);
    if (!target) return;
    
    // Show loading indicator
    target.innerHTML = '<div class="loading">Loading...</div>';
    
    // Fetch content
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(html => {
            target.innerHTML = html;
        })
        .catch(error => {
            target.innerHTML = `<div class="error">Error loading content: ${error.message}</div>`;
        });
}

/**
 * Initialize image sliders
 * @param {string} sliderId - The ID of the slider container
 */
function initSlider(sliderId) {
    const slider = document.getElementById(sliderId);
    if (!slider) return;
    
    const slides = slider.querySelectorAll('.slide');
    if (slides.length === 0) return;
    
    let currentSlide = 0;
    
    // Show initial slide
    slides[0].classList.add('active');
    
    // Create navigation dots
    const dotsContainer = document.createElement('div');
    dotsContainer.className = 'slider-dots';
    
    for (let i = 0; i < slides.length; i++) {
        const dot = document.createElement('span');
        dot.className = i === 0 ? 'dot active' : 'dot';
        dot.addEventListener('click', () => {
            goToSlide(i);
        });
        dotsContainer.appendChild(dot);
    }
    
    slider.appendChild(dotsContainer);
    
    // Create prev/next buttons
    const prevBtn = document.createElement('button');
    prevBtn.className = 'slider-btn prev';
    prevBtn.innerHTML = '&lt;';
    prevBtn.addEventListener('click', () => {
        goToSlide(currentSlide - 1);
    });
    
    const nextBtn = document.createElement('button');
    nextBtn.className = 'slider-btn next';
    nextBtn.innerHTML = '&gt;';
    nextBtn.addEventListener('click', () => {
        goToSlide(currentSlide + 1);
    });
    
    slider.appendChild(prevBtn);
    slider.appendChild(nextBtn);
    
    // Function to go to a specific slide
    function goToSlide(n) {
        slides[currentSlide].classList.remove('active');
        dotsContainer.children[currentSlide].classList.remove('active');
        
        currentSlide = (n + slides.length) % slides.length;
        
        slides[currentSlide].classList.add('active');
        dotsContainer.children[currentSlide].classList.add('active');
    }
    
    // Auto advance slides every 5 seconds
    setInterval(() => {
        goToSlide(currentSlide + 1);
    }, 5000);
}