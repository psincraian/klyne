// Theme switcher module for Klyne
// Handles dark/light mode switching with system preference detection

class ThemeSwitcher {
  constructor() {
    this.STORAGE_KEY = 'klyne-theme-preference';
    this.LIGHT_THEME = 'klyne';
    this.DARK_THEME = 'klyne-dark';
    this.SYSTEM_PREFERENCE = 'system';
    
    this.init();
  }

  init() {
    // Apply theme immediately to prevent flash
    this.applyTheme();
    
    // Set up event listeners
    this.setupEventListeners();
    
    // Update toggle button state
    this.updateToggleButtons();
  }

  getCurrentTheme() {
    const savedPreference = localStorage.getItem(this.STORAGE_KEY);
    
    if (savedPreference && savedPreference !== this.SYSTEM_PREFERENCE) {
      return savedPreference;
    }
    
    // Use system preference
    return this.getSystemPreference();
  }

  getSystemPreference() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return this.DARK_THEME;
    }
    return this.LIGHT_THEME;
  }

  getUserPreference() {
    return localStorage.getItem(this.STORAGE_KEY) || this.SYSTEM_PREFERENCE;
  }

  setTheme(theme) {
    localStorage.setItem(this.STORAGE_KEY, theme);
    this.applyTheme();
    this.updateToggleButtons();
  }

  applyTheme() {
    const theme = this.getCurrentTheme();
    document.documentElement.setAttribute('data-theme', theme);
  }

  toggleTheme() {
    const currentTheme = this.getCurrentTheme();
    const newTheme = currentTheme === this.LIGHT_THEME ? this.DARK_THEME : this.LIGHT_THEME;
    this.setTheme(newTheme);
  }

  setupEventListeners() {
    // Listen for system preference changes
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addEventListener('change', () => {
        // Only apply system change if user hasn't set a manual preference
        if (this.getUserPreference() === this.SYSTEM_PREFERENCE) {
          this.applyTheme();
          this.updateToggleButtons();
        }
      });
    }

    // Set up theme toggle buttons
    document.addEventListener('click', (e) => {
      if (e.target.closest('[data-theme-toggle]')) {
        e.preventDefault();
        this.toggleTheme();
      }
    });
  }

  updateToggleButtons() {
    const buttons = document.querySelectorAll('[data-theme-toggle]');
    const currentTheme = this.getCurrentTheme();
    const isDark = currentTheme === this.DARK_THEME;

    buttons.forEach(button => {
      const sunIcon = button.querySelector('.theme-icon-sun');
      const moonIcon = button.querySelector('.theme-icon-moon');
      
      if (sunIcon && moonIcon) {
        if (isDark) {
          sunIcon.classList.remove('hidden');
          moonIcon.classList.add('hidden');
          button.title = 'Switch to light mode';
        } else {
          sunIcon.classList.add('hidden');
          moonIcon.classList.remove('hidden');
          button.title = 'Switch to dark mode';
        }
      }
    });
  }

  resetToSystem() {
    this.setTheme(this.SYSTEM_PREFERENCE);
  }

  isUsingSystemPreference() {
    return this.getUserPreference() === this.SYSTEM_PREFERENCE;
  }

  isDarkMode() {
    return this.getCurrentTheme() === this.DARK_THEME;
  }
}

// Initialize theme switcher when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.themeSwitcher = new ThemeSwitcher();
  });
} else {
  window.themeSwitcher = new ThemeSwitcher();
}

// Export for module usage
export default ThemeSwitcher;