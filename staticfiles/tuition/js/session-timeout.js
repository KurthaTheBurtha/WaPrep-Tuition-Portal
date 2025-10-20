// Session Timeout Management
class SessionTimeoutManager {
    constructor() {
        this.timeoutDuration = 15 * 60 * 1000; // 15 minutes in milliseconds
        this.warningDuration = 2 * 60 * 1000; // 2 minutes warning
        this.timeoutId = null;
        this.warningId = null;
        this.isWarningShown = false;
        this.lastActivity = Date.now();
        
        this.init();
    }
    
    init() {
        // Reset timer on user activity
        this.resetTimer();
        
        // Track user activity
        this.trackActivity();
        
        // Start the timeout timer
        this.startTimeout();
    }
    
    trackActivity() {
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        events.forEach(event => {
            document.addEventListener(event, () => {
                this.resetTimer();
            }, true);
        });
    }
    
    resetTimer() {
        this.lastActivity = Date.now();
        
        // Clear existing timers
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
        }
        if (this.warningId) {
            clearTimeout(this.warningId);
        }
        
        // Hide warning if it's shown
        if (this.isWarningShown) {
            this.hideWarning();
        }
        
        // Start new timers
        this.startTimeout();
    }
    
    startTimeout() {
        // Set warning timer
        this.warningId = setTimeout(() => {
            this.showWarning();
        }, this.timeoutDuration - this.warningDuration);
        
        // Set logout timer
        this.timeoutId = setTimeout(() => {
            this.logout();
        }, this.timeoutDuration);
    }
    
    showWarning() {
        this.isWarningShown = true;
        
        // Create warning modal
        const warningModal = document.createElement('div');
        warningModal.id = 'sessionWarningModal';
        warningModal.className = 'modal fade show';
        warningModal.style.display = 'block';
        warningModal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        warningModal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-warning">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle me-2"></i>Session Timeout Warning
                        </h5>
                    </div>
                    <div class="modal-body">
                        <p>Your session will expire in <strong id="countdown">2:00</strong> due to inactivity.</p>
                        <p>Click "Stay Logged In" to continue your session, or you will be automatically logged out.</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="sessionManager.logout()">
                            Logout Now
                        </button>
                        <button type="button" class="btn btn-primary" onclick="sessionManager.resetTimer()">
                            Stay Logged In
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(warningModal);
        
        // Start countdown
        this.startCountdown();
    }
    
    hideWarning() {
        this.isWarningShown = false;
        const warningModal = document.getElementById('sessionWarningModal');
        if (warningModal) {
            warningModal.remove();
        }
    }
    
    startCountdown() {
        let timeLeft = this.warningDuration / 1000; // Convert to seconds
        
        const countdownElement = document.getElementById('countdown');
        if (!countdownElement) return;
        
        const countdownInterval = setInterval(() => {
            timeLeft--;
            
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            
            countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
                this.logout();
            }
        }, 1000);
    }
    
    logout() {
        // Send AJAX request to logout
        fetch('/ajax-logout/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            // Redirect to login page
            window.location.href = '/login/payer/';
        })
        .catch(error => {
            console.error('Logout error:', error);
            // Fallback redirect
            window.location.href = '/login/payer/';
        });
    }
    
    getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            return csrfToken.value;
        }
        
        // Fallback: try to get from cookie
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Initialize session timeout manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if user is logged in (check for logout link or user-specific elements)
    if (document.querySelector('a[href*="logout"]') || document.querySelector('.user-info')) {
        window.sessionManager = new SessionTimeoutManager();
    }
}); 