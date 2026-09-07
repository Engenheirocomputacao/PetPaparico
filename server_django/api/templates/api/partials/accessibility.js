/**
 * Sistema de Acessibilidade - Pet Paparico
 * Funcionalidades:
 * - Aumento/diminuição de fonte
 * - Alto contraste
 * - VLibras
 * - Preferências persistentes
 */

(function() {
    'use strict';

    const AccessibilityManager = {
        // Configurações padrão
        defaults: {
            fontSize: 100, // porcentagem
            highContrast: false,
            vlibras: true
        },

        // Limites
        limits: {
            minFontSize: 80,
            maxFontSize: 150,
            fontSizeStep: 10
        },

        // Inicialização
        init() {
            this.loadPreferences();
            this.applyPreferences();
            this.createToolbar();
            this.initVLibras();
            this.bindKeyboardShortcuts();
        },

        // Carregar preferências do localStorage
        loadPreferences() {
            try {
                const saved = localStorage.getItem('petPaparicoAccessibility');
                if (saved) {
                    this.preferences = { ...this.defaults, ...JSON.parse(saved) };
                } else {
                    this.preferences = { ...this.defaults };
                }
            } catch (e) {
                this.preferences = { ...this.defaults };
            }
        },

        // Salvar preferências
        savePreferences() {
            try {
                localStorage.setItem('petPaparicoAccessibility', JSON.stringify(this.preferences));
            } catch (e) {
                console.warn('Não foi possível salvar preferências de acessibilidade:', e);
            }
        },

        // Aplicar preferências
        applyPreferences() {
            this.applyFontSize();
            this.applyHighContrast();
        },

        // Aplicar tamanho da fonte
        applyFontSize() {
            document.documentElement.style.fontSize = `${this.preferences.fontSize}%`;
        },

        // Aplicar alto contraste
        applyHighContrast() {
            if (this.preferences.highContrast) {
                document.body.classList.add('high-contrast');
            } else {
                document.body.classList.remove('high-contrast');
            }
        },

        // Aumentar fonte
        increaseFontSize() {
            if (this.preferences.fontSize < this.limits.maxFontSize) {
                this.preferences.fontSize += this.limits.fontSizeStep;
                this.applyFontSize();
                this.savePreferences();
                this.updateToolbarUI();
                this.announce(`Tamanho da fonte aumentado para ${this.preferences.fontSize}%`);
            }
        },

        // Diminuir fonte
        decreaseFontSize() {
            if (this.preferences.fontSize > this.limits.minFontSize) {
                this.preferences.fontSize -= this.limits.fontSizeStep;
                this.applyFontSize();
                this.savePreferences();
                this.updateToolbarUI();
                this.announce(`Tamanho da fonte diminuído para ${this.preferences.fontSize}%`);
            }
        },

        // Resetar fonte
        resetFontSize() {
            this.preferences.fontSize = this.defaults.fontSize;
            this.applyFontSize();
            this.savePreferences();
            this.updateToolbarUI();
            this.announce('Tamanho da fonte restaurado ao padrão');
        },

        // Alternar alto contraste
        toggleHighContrast() {
            this.preferences.highContrast = !this.preferences.highContrast;
            this.applyHighContrast();
            this.savePreferences();
            this.updateToolbarUI();
            const status = this.preferences.highContrast ? 'ativado' : 'desativado';
            this.announce(`Alto contraste ${status}`);
        },

        // Criar toolbar de acessibilidade
        createToolbar() {
            const toolbar = document.createElement('div');
            toolbar.id = 'accessibility-toolbar';
            toolbar.setAttribute('role', 'toolbar');
            toolbar.setAttribute('aria-label', 'Ferramentas de acessibilidade');
            toolbar.innerHTML = `
                <button 
                    type="button"
                    id="a11y-decrease-font"
                    class="a11y-btn"
                    aria-label="Diminuir tamanho da fonte"
                    title="Diminuir fonte (Ctrl + -)"
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    <span class="a11y-btn-label">A-</span>
                </button>
                
                <button 
                    type="button"
                    id="a11y-increase-font"
                    class="a11y-btn"
                    aria-label="Aumentar tamanho da fonte"
                    title="Aumentar fonte (Ctrl + +)"
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    <span class="a11y-btn-label">A+</span>
                </button>
                
                <button 
                    type="button"
                    id="a11y-reset-font"
                    class="a11y-btn"
                    aria-label="Restaurar tamanho padrão da fonte"
                    title="Restaurar fonte padrão (Ctrl + 0)"
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
                        <path d="M3 3v5h5"></path>
                    </svg>
                    <span class="a11y-btn-label">Reset</span>
                </button>
                
                <button 
                    type="button"
                    id="a11y-contrast"
                    class="a11y-btn"
                    aria-label="Alternar alto contraste"
                    title="Alto contraste (Ctrl + C)"
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <path d="M12 2a10 10 0 0 1 0 20z" fill="currentColor"></path>
                    </svg>
                    <span class="a11y-btn-label">Contraste</span>
                </button>
                
                <button 
                    type="button"
                    id="a11y-toggle"
                    class="a11y-btn a11y-toggle-btn"
                    aria-label="Fechar toolbar de acessibilidade"
                    title="Fechar toolbar"
                >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                </button>
            `;

            // Adicionar estilos
            const style = document.createElement('style');
            style.textContent = this.getToolbarStyles();
            document.head.appendChild(style);

            // Adicionar toolbar ao body
            document.body.appendChild(toolbar);

            // Bind events
            this.bindToolbarEvents();
        },

        // Estilos da toolbar
        getToolbarStyles() {
            return `
                /* Toolbar de Acessibilidade */
                #accessibility-toolbar {
                    position: fixed;
                    top: 50%;
                    right: 0;
                    transform: translateY(-50%);
                    z-index: 999999;
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                    padding: 8px;
                    background: #ffffff;
                    border: 2px solid #e2e8f0;
                    border-right: none;
                    border-radius: 12px 0 0 12px;
                    box-shadow: -2px 0 8px rgba(0,0,0,0.1);
                    transition: all 0.3s ease;
                }

                #accessibility-toolbar.hidden {
                    right: -60px;
                }

                .a11y-btn {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 2px;
                    padding: 8px 12px;
                    background: #f8fafc;
                    border: 2px solid #e2e8f0;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    color: #1e293b;
                    font-weight: 600;
                    font-size: 12px;
                    min-width: 50px;
                }

                .a11y-btn:hover {
                    background: #e0e7ff;
                    border-color: #6366f1;
                    color: #4f46e5;
                    transform: scale(1.05);
                }

                .a11y-btn:focus {
                    outline: 3px solid #6366f1;
                    outline-offset: 2px;
                }

                .a11y-btn:active {
                    transform: scale(0.95);
                }

                .a11y-btn-label {
                    font-size: 10px;
                    line-height: 1;
                }

                .a11y-toggle-btn {
                    margin-top: 4px;
                    border-top: 2px solid #e2e8f0;
                    padding-top: 12px;
                }

                /* Alto Contraste */
                body.high-contrast {
                    background: #000000 !important;
                    color: #ffffff !important;
                }

                body.high-contrast * {
                    background-color: #000000 !important;
                    color: #ffffff !important;
                    border-color: #ffffff !important;
                }

                body.high-contrast a,
                body.high-contrast button {
                    color: #ffff00 !important;
                }

                body.high-contrast input,
                body.high-contrast select,
                body.high-contrast textarea {
                    background: #000000 !important;
                    color: #ffffff !important;
                    border: 2px solid #ffffff !important;
                }

                body.high-contrast img {
                    filter: grayscale(100%) contrast(150%);
                }

                /* Responsividade */
                @media (max-width: 768px) {
                    #accessibility-toolbar {
                        top: auto;
                        bottom: 80px;
                        right: 0;
                        transform: none;
                        flex-direction: row;
                        border-radius: 12px 0 0 12px;
                    }

                    #accessibility-toolbar.hidden {
                        right: -60px;
                        bottom: 80px;
                    }

                    .a11y-btn {
                        padding: 6px 8px;
                        min-width: 40px;
                    }
                }

                /* Skip Link */
                .skip-link {
                    position: absolute;
                    top: -40px;
                    left: 0;
                    background: #6366f1;
                    color: white;
                    padding: 8px 16px;
                    z-index: 1000000;
                    transition: top 0.3s;
                    font-weight: 600;
                }

                .skip-link:focus {
                    top: 0;
                }
            `;
        },

        // Bind events da toolbar
        bindToolbarEvents() {
            document.getElementById('a11y-decrease-font')?.addEventListener('click', () => this.decreaseFontSize());
            document.getElementById('a11y-increase-font')?.addEventListener('click', () => this.increaseFontSize());
            document.getElementById('a11y-reset-font')?.addEventListener('click', () => this.resetFontSize());
            document.getElementById('a11y-contrast')?.addEventListener('click', () => this.toggleHighContrast());
            
            document.getElementById('a11y-toggle')?.addEventListener('click', () => {
                const toolbar = document.getElementById('accessibility-toolbar');
                toolbar?.classList.toggle('hidden');
            });
        },

        // Atualizar UI da toolbar
        updateToolbarUI() {
            const contrastBtn = document.getElementById('a11y-contrast');
            if (contrastBtn) {
                if (this.preferences.highContrast) {
                    contrastBtn.style.background = '#ffff00';
                    contrastBtn.style.color = '#000000';
                    contrastBtn.style.borderColor = '#ffff00';
                } else {
                    contrastBtn.style.background = '';
                    contrastBtn.style.color = '';
                    contrastBtn.style.borderColor = '';
                }
            }
        },

        // Inicializar VLibras
        initVLibras() {
            if (!this.preferences.vlibras) return;

            // Verificar se já foi carregado
            if (document.getElementById('vlibras-plugin')) return;

            // Criar container do VLibras
            const vw = document.createElement('div');
            vw.setAttribute('vw');
            vw.setAttribute('class', 'vlibras-container');
            document.body.appendChild(vw);

            // Carregar script do VLibras
            const script = document.createElement('script');
            script.id = 'vlibras-plugin';
            script.src = 'https://vlibras.gov.br/app/vlibras-plugin.js';
            script.async = true;
            script.onload = () => {
                new window.VLibras.Widget('https://vlibras.gov.br/app');
            };
            document.head.appendChild(script);
        },

        // Atalhos de teclado
        bindKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Ctrl + + para aumentar fonte
                if (e.ctrlKey && (e.key === '+' || e.key === '=')) {
                    e.preventDefault();
                    this.increaseFontSize();
                }
                
                // Ctrl + - para diminuir fonte
                if (e.ctrlKey && e.key === '-') {
                    e.preventDefault();
                    this.decreaseFontSize();
                }
                
                // Ctrl + 0 para resetar fonte
                if (e.ctrlKey && e.key === '0') {
                    e.preventDefault();
                    this.resetFontSize();
                }
                
                // Ctrl + C para alto contraste
                if (e.ctrlKey && e.key === 'c' && !window.getSelection().toString()) {
                    e.preventDefault();
                    this.toggleHighContrast();
                }
            });
        },

        // Anunciar para leitores de tela
        announce(message) {
            let announcer = document.getElementById('a11y-announcer');
            if (!announcer) {
                announcer = document.createElement('div');
                announcer.id = 'a11y-announcer';
                announcer.setAttribute('aria-live', 'polite');
                announcer.setAttribute('aria-atomic', 'true');
                announcer.className = 'sr-only';
                document.body.appendChild(announcer);
            }
            announcer.textContent = message;
        }
    };

    // Inicializar quando DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => AccessibilityManager.init());
    } else {
        AccessibilityManager.init();
    }

    // Expor globalmente para uso externo
    window.AccessibilityManager = AccessibilityManager;
})();
