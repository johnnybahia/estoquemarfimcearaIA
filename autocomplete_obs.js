/**
 * AutoComplete OBS — Marfim Estoque Ceará
 * ========================================
 * Componente reutilizável de autocomplete para campos de observação.
 *
 * Busca incremental com fuzzy matching da direita para esquerda.
 * Carrega automaticamente os valores da coluna F da aba DADOS.
 *
 * Uso:
 *   <input type="text" id="meu-campo-obs" class="form-control" />
 *   <script>
 *     AutoCompleteOBS.init('meu-campo-obs');
 *   </script>
 *
 * Ou para inicializar vários campos de uma vez:
 *   AutoCompleteOBS.initAll(['entrada-obs', 'saida-obs', 'conf-obs']);
 */

(function(window) {
  'use strict';

  // ─────────────────────────────────────────────────────────
  // Estado global
  // ─────────────────────────────────────────────────────────
  let observacoesCache = [];
  let cacheTimestamp = null;
  const CACHE_TTL_MS = 5 * 60 * 1000;  // 5 minutos
  const instancias = new Map();
  const DEBUG = true;  // Ativar logs de debug

  function log(...args) {
    if (DEBUG) console.log('[AutoCompleteOBS]', ...args);
  }

  // ─────────────────────────────────────────────────────────
  // Helpers
  // ─────────────────────────────────────────────────────────

  /**
   * Busca fuzzy — retorna true se `query` aparece em `texto`
   * em qualquer posição (direita → esquerda tolerante).
   */
  function matchFuzzy(texto, query) {
    if (!query || query.trim() === '') return true;
    const t = removerAcentos(texto.toLowerCase());
    const q = removerAcentos(query.toLowerCase());
    return t.includes(q);
  }

  /**
   * Remove acentuação para busca mais tolerante.
   */
  function removerAcentos(str) {
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  /**
   * Carrega observações do endpoint ou retorna do cache se válido.
   */
  async function carregarObservacoes(forceRefresh = false) {
    const agora = Date.now();
    if (!forceRefresh && cacheTimestamp && (agora - cacheTimestamp < CACHE_TTL_MS)) {
      log(`Usando cache (${observacoesCache.length} observações)`);
      return observacoesCache;
    }

    log('Carregando observações do servidor...');
    try {
      const response = await fetch('/api/dados-auxiliares');
      const data = await response.json();
      if (data.success && data.observacoes) {
        observacoesCache = data.observacoes;
        cacheTimestamp = agora;
        log(`✅ Carregadas ${observacoesCache.length} observações:`, observacoesCache);
        return observacoesCache;
      }
      log('⚠️ Resposta sem observações:', data);
      return [];
    } catch (e) {
      console.error('[AutoCompleteOBS] Erro ao carregar observações:', e);
      return observacoesCache;  // retorna cache antigo se der erro
    }
  }

  /**
   * Invalida o cache — use após adicionar nova observação.
   */
  function invalidarCache() {
    cacheTimestamp = null;
  }

  // ─────────────────────────────────────────────────────────
  // Classe AutoComplete para cada input
  // ─────────────────────────────────────────────────────────
  class AutoCompleteInstance {
    constructor(inputId) {
      this.inputId = inputId;
      this.input = document.getElementById(inputId);
      if (!this.input) {
        console.error(`[AutoCompleteOBS] Input com id "${inputId}" não encontrado.`);
        return;
      }

      log(`Inicializando autocomplete para #${inputId}`);

      this.dropdown = null;
      this.items = [];
      this.selectedIndex = -1;
      this.debounceTimer = null;

      this._criarDropdown();
      this._attachEventos();
      log(`✅ Autocomplete #${inputId} inicializado com sucesso`);
    }

    _criarDropdown() {
      // Cria o dropdown se não existir
      let container = this.input.parentElement;
      if (!container.classList.contains('autocomplete-container')) {
        // Wrap o input em uma div
        const wrapper = document.createElement('div');
        wrapper.className = 'autocomplete-container';
        wrapper.style.position = 'relative';
        this.input.parentNode.insertBefore(wrapper, this.input);
        wrapper.appendChild(this.input);
        container = wrapper;
      }

      // Cria lista de sugestões
      this.dropdown = document.createElement('div');
      this.dropdown.className = 'autocomplete-list autocomplete-obs-dropdown';
      this.dropdown.style.cssText = `
        position: absolute !important;
        top: 100% !important;
        left: 0 !important;
        right: 0 !important;
        background: white !important;
        border: 2px solid #0d6efd !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
        max-height: 280px !important;
        overflow-y: auto !important;
        z-index: 9999 !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.2) !important;
        display: none !important;
        margin-top: 0 !important;
      `;
      container.appendChild(this.dropdown);
    }

    _attachEventos() {
      // Input → busca com debounce
      this.input.addEventListener('input', (e) => {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
          this._buscar(e.target.value);
        }, 200);
      });

      // Focus → mostra dropdown
      this.input.addEventListener('focus', () => {
        this._buscar(this.input.value);
      });

      // Navegação com teclado
      this.input.addEventListener('keydown', (e) => {
        if (!this.dropdown.style.display || this.dropdown.style.display === 'none') {
          return;
        }

        if (e.key === 'ArrowDown') {
          e.preventDefault();
          this._moverSelecao(1);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this._moverSelecao(-1);
        } else if (e.key === 'Enter') {
          if (this.selectedIndex >= 0 && this.items[this.selectedIndex]) {
            e.preventDefault();
            this._selecionar(this.selectedIndex);
          }
        } else if (e.key === 'Escape') {
          this._fechar();
        }
      });

      // Fechar ao clicar fora
      document.addEventListener('click', (e) => {
        if (!this.input.contains(e.target) && !this.dropdown.contains(e.target)) {
          this._fechar();
        }
      });
    }

    async _buscar(query) {
      log(`Buscando observações para query: "${query}"`);
      const obs = await carregarObservacoes();
      log(`Total de observações no cache: ${obs.length}`);

      // Filtrar com fuzzy match
      const filtrados = obs.filter(o => matchFuzzy(o, query));
      log(`Encontradas ${filtrados.length} correspondências para "${query}"`);

      // Limita a 15 resultados
      this.items = filtrados.slice(0, 15);
      this.selectedIndex = -1;

      if (this.items.length === 0) {
        log(`Nenhum resultado para "${query}" — fechando dropdown`);
        this._fechar();
        return;
      }

      log(`Renderizando ${this.items.length} itens`);
      this._renderizar(query);
    }

    _renderizar(query) {
      this.dropdown.innerHTML = '';

      this.items.forEach((item, idx) => {
        const div = document.createElement('div');
        div.className = 'autocomplete-item';
        div.style.cssText = `
          padding: 10px 15px;
          cursor: pointer;
          border-bottom: 1px solid #f0f0f0;
          transition: background 0.15s;
        `;

        // Highlight da query
        const highlightedText = this._highlight(item, query);
        div.innerHTML = `<span class="item-nome">${highlightedText}</span>`;

        // Eventos
        div.addEventListener('mouseenter', () => {
          this._highlightItem(idx);
        });
        div.addEventListener('click', () => {
          this._selecionar(idx);
        });

        this.dropdown.appendChild(div);
      });

      // Adiciona opção "Adicionar novo" se houver query
      if (query && query.trim() && !this.items.includes(query.trim())) {
        const divNovo = document.createElement('div');
        divNovo.className = 'autocomplete-item autocomplete-item-novo';
        divNovo.style.cssText = `
          padding: 10px 15px;
          cursor: pointer;
          border-top: 2px solid #eee;
          background: #f8f9fa;
          font-weight: 600;
          color: #0d6efd;
        `;
        divNovo.innerHTML = `<span>✚ Usar "${query.trim()}"</span>`;
        divNovo.addEventListener('click', () => {
          this.input.value = query.trim();
          this._fechar();
          this.input.dispatchEvent(new Event('change', { bubbles: true }));
        });
        this.dropdown.appendChild(divNovo);
      }

      this.dropdown.style.display = 'block';
      log(`Dropdown exibido para #${this.inputId} (${this.items.length} itens + ${query && query.trim() && !this.items.includes(query.trim()) ? 1 : 0} novo)`);
    }

    _highlight(texto, query) {
      if (!query || !query.trim()) return texto;
      const q = removerAcentos(query.toLowerCase());
      const t = removerAcentos(texto.toLowerCase());
      const idx = t.indexOf(q);
      if (idx === -1) return texto;

      const before = texto.slice(0, idx);
      const match = texto.slice(idx, idx + query.length);
      const after = texto.slice(idx + query.length);
      return `${before}<strong style="background:#fff3cd;color:#856404;padding:0 2px">${match}</strong>${after}`;
    }

    _moverSelecao(delta) {
      const itemsElements = this.dropdown.querySelectorAll('.autocomplete-item:not(.autocomplete-item-novo)');
      if (itemsElements.length === 0) return;

      this.selectedIndex += delta;
      if (this.selectedIndex < 0) this.selectedIndex = itemsElements.length - 1;
      if (this.selectedIndex >= itemsElements.length) this.selectedIndex = 0;

      this._highlightItem(this.selectedIndex);
      itemsElements[this.selectedIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    _highlightItem(idx) {
      const itemsElements = this.dropdown.querySelectorAll('.autocomplete-item:not(.autocomplete-item-novo)');
      itemsElements.forEach((el, i) => {
        if (i === idx) {
          el.style.background = '#e7f1ff';
        } else {
          el.style.background = 'white';
        }
      });
      this.selectedIndex = idx;
    }

    _selecionar(idx) {
      if (idx < 0 || idx >= this.items.length) return;
      this.input.value = this.items[idx];
      this._fechar();
      this.input.dispatchEvent(new Event('change', { bubbles: true }));
      this.input.focus();
    }

    _fechar() {
      this.dropdown.style.display = 'none';
      this.selectedIndex = -1;
    }

    destruir() {
      if (this.dropdown && this.dropdown.parentNode) {
        this.dropdown.parentNode.removeChild(this.dropdown);
      }
    }
  }

  // ─────────────────────────────────────────────────────────
  // API Pública
  // ─────────────────────────────────────────────────────────
  window.AutoCompleteOBS = {
    /**
     * Inicializa autocomplete em um input específico.
     * @param {string} inputId - ID do elemento input
     * @returns {AutoCompleteInstance}
     */
    init: function(inputId) {
      if (instancias.has(inputId)) {
        console.warn(`[AutoCompleteOBS] Input "${inputId}" já possui autocomplete.`);
        return instancias.get(inputId);
      }
      const instance = new AutoCompleteInstance(inputId);
      instancias.set(inputId, instance);
      return instance;
    },

    /**
     * Inicializa autocomplete em múltiplos inputs.
     * @param {string[]} inputIds - Array de IDs
     */
    initAll: function(inputIds) {
      inputIds.forEach(id => this.init(id));
    },

    /**
     * Remove autocomplete de um input.
     * @param {string} inputId
     */
    destroy: function(inputId) {
      const instance = instancias.get(inputId);
      if (instance) {
        instance.destruir();
        instancias.delete(inputId);
      }
    },

    /**
     * Invalida o cache de observações.
     * Use após adicionar nova observação via modal.
     */
    refresh: function() {
      invalidarCache();
      carregarObservacoes(true).then(obs => {
        console.log(`[AutoCompleteOBS] Cache atualizado — ${obs.length} observações.`);
      });
    },

    /**
     * Pré-carrega as observações no cache.
     */
    preload: function() {
      carregarObservacoes();
    },

    /**
     * Retorna o cache atual de observações.
     */
    getCache: function() {
      return observacoesCache;
    }
  };

  // Auto-inicialização ao carregar DOM
  document.addEventListener('DOMContentLoaded', function() {
    log('DOMContentLoaded — procurando campos OBS para auto-inicialização...');

    // Procura automaticamente todos os inputs dentro de .autocomplete-container
    const containers = document.querySelectorAll('.autocomplete-container');
    log(`Encontrados ${containers.length} containers com classe .autocomplete-container`);

    containers.forEach((container, idx) => {
      const input = container.querySelector('input[type="text"], input:not([type])');
      if (input && input.id) {
        log(`  [${idx + 1}] Container → input#${input.id}`);
        window.AutoCompleteOBS.init(input.id);
      } else {
        log(`  [${idx + 1}] Container sem input válido (precisa ter id e type="text")`);
      }
    });

    // Pré-carrega observações
    log('Pré-carregando observações...');
    window.AutoCompleteOBS.preload();
  });

})(window);
