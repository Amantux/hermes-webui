
const App = {
    state: {
        currentRoute: 'dashboard',
        activeModel: 'gemma4:31b'
    },
    init() {
        this.bindEvents();
        this.navigate('dashboard');
    },
    bindEvents() {
        window.addEventListener('keydown', e => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                this.togglePalette();
            }
        });
    },
    togglePalette() {
        const p = document.getElementById('palette');
        if (p) p.style.display = p.style.display === 'block' ? 'none' : 'block';
    },
    async navigate(route) {
        this.state.currentRoute = route;
        const content = document.getElementById('main-content');
        if (!content) return;

        switch(route) {
            case 'dashboard':
                content.innerHTML = `<h1 class="emerald-text">HERMES COMMAND</h1>` + ChatComponent.render();
                ChatComponent.init();
                break;
            case 'workspace':
                content.innerHTML = await WorkspaceComponent.render();
                break;
            case 'kanban':
                content.innerHTML = await KanbanComponent.render();
                break;
            case 'models':
                const res = await fetch('/api/status');
                const data = await res.json();
                content.innerHTML = `<h1 class="emerald-text">MODEL REGISTRY</h1><p>Active: ${data.active}</p>
                                     <button class="emerald-btn" onclick="App.switchModel('hermes-3-llama-8b')">Switch to Hermes-3</button>`;
                break;
        }
    },
    async switchModel(id) {
        await fetch('/api/model/set', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({model_id: id})
        });
        this.navigate('models');
    }
};
document.addEventListener('DOMContentLoaded', () => App.init());
