
const MonitoringUI = {
    async update() {
        const res = await fetch('/api/metrics');
        const data = await res.json();
        
        // Update text values
        document.getElementById('cpu').innerText = data.current.cpu + '%';
        document.getElementById('ram').innerText = data.current.ram + '%';
        
        // Update Sparklines
        this.drawChart('cpu-chart', data.history.cpu);
        this.drawChart('ram-chart', data.history.ram);
    },
    drawChart(id, values) {
        const canvas = document.getElementById(id);
        if(!canvas) return;
        
        const width = 260;
        const height = 40;
        const step = width / (values.length - 1 || 1);
        
        let path = `M 0 ${height - (values[0] || 0) * (height/100)}`;
        values.forEach((v, i) => {
            path += ` L ${i * step} ${height - (v * (height/100))}`;
        });
        
        canvas.setAttribute('d', path);
    },
    start() {
        setInterval(() => this.update(), 2000);
    }
};
document.addEventListener('DOMContentLoaded', () => MonitoringUI.start());
