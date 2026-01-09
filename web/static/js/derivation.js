/**
 * Derivation Visualization - vis-network graphs
 * 
 * Viz 1: Metrics → Archetype Matching
 * Viz 2: Archetype → Prompt Assembly
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // =============================================================================
    // COLLAPSIBLE TOGGLE
    // =============================================================================
    
    const toggle = document.getElementById('derivation-toggle');
    const content = document.getElementById('derivation-content');
    const section = document.querySelector('.derivation-section');
    
    let graphsInitialized = false;
    
    if (toggle && content) {
        toggle.addEventListener('click', function() {
            const isExpanded = section.classList.toggle('expanded');
            content.style.display = isExpanded ? 'block' : 'none';
            
            // Initialize graphs on first expand
            if (isExpanded && !graphsInitialized) {
                initDerivationGraphs();
                graphsInitialized = true;
            }
        });
    }
    
    // =============================================================================
    // COLORS
    // =============================================================================
    
    const COLORS = {
        bg: '#0a0a0a',
        node: '#2a2a2a',
        nodeBorder: '#444444',
        nodeHighlight: '#666666',
        text: '#e0e0e0',
        textDim: '#808080',
        edge: '#404040',
        edgeHighlight: '#808080',
        // Metric colors
        valence: '#66cc66',
        tension: '#cc6666',
        hope: '#6699cc',
        energy: '#cccc66',
        // Archetype colors (muted)
        primary: '#a0a0a0',
        secondary: '#707070',
        inactive: '#404040',
        // Prompt components
        genre: '#8888aa',
        instruments: '#88aa88',
        moods: '#aa8888',
        tempo: '#aaaa88',
    };
    
    // =============================================================================
    // FETCH DATA & INIT
    // =============================================================================
    
    async function initDerivationGraphs() {
        try {
            const response = await fetch('/api/derivation');
            const data = await response.json();
            
            if (data.error) {
                console.error('[Derivation] Error:', data.error);
                return;
            }
            
            buildMetricMatchingGraph(data);
            buildPromptAssemblyGraph(data);
            
        } catch (e) {
            console.error('[Derivation] Failed to load data:', e);
        }
    }
    
    // =============================================================================
    // VIZ 1: METRIC → ARCHETYPE MATCHING
    // =============================================================================
    
    function buildMetricMatchingGraph(data) {
        const container = document.getElementById('graph-metric-matching');
        if (!container) return;
        
        const nodes = [];
        const edges = [];
        
        const metrics = data.input_metrics;
        const selection = data.selection;
        const allScores = selection.all_scores || [];
        
        // Metric nodes (left side)
        const metricDefs = [
            { id: 'm_valence', label: `Valence\n${metrics.valence >= 0 ? '+' : ''}${metrics.valence.toFixed(2)}`, color: COLORS.valence },
            { id: 'm_tension', label: `Tension\n${metrics.tension.toFixed(2)}`, color: COLORS.tension },
            { id: 'm_hope', label: `Hope\n${metrics.hope.toFixed(2)}`, color: COLORS.hope },
            { id: 'm_energy', label: `Energy\n${metrics.energy}`, color: COLORS.energy },
        ];
        
        metricDefs.forEach((m, i) => {
            nodes.push({
                id: m.id,
                label: m.label,
                x: -250,
                y: -120 + (i * 80),
                fixed: true,
                shape: 'box',
                color: {
                    background: COLORS.node,
                    border: m.color,
                    highlight: { background: COLORS.nodeHighlight, border: m.color },
                },
                font: { color: COLORS.text, size: 11, face: 'IBM Plex Mono, monospace' },
                borderWidth: 2,
            });
        });
        
        // Archetype nodes (right side)
        allScores.forEach((item, i) => {
            const isPrimary = item.archetype === selection.primary;
            const isSecondary = item.archetype === selection.secondary;
            
            let borderColor = COLORS.inactive;
            let borderWidth = 1;
            if (isPrimary) {
                borderColor = COLORS.primary;
                borderWidth = 3;
            } else if (isSecondary) {
                borderColor = COLORS.secondary;
                borderWidth = 2;
            }
            
            const displayName = item.archetype.replace(/_/g, ' ');
            const scorePercent = Math.round(item.score * 100);
            
            nodes.push({
                id: `a_${item.archetype}`,
                label: `${displayName}\n${scorePercent}%`,
                x: 250,
                y: -150 + (i * 60),
                fixed: true,
                shape: 'box',
                color: {
                    background: COLORS.node,
                    border: borderColor,
                    highlight: { background: COLORS.nodeHighlight, border: borderColor },
                },
                font: { 
                    color: isPrimary ? COLORS.text : (isSecondary ? COLORS.textDim : '#505050'),
                    size: 10,
                    face: 'IBM Plex Mono, monospace',
                },
                borderWidth: borderWidth,
            });
            
            // Edges from metrics to this archetype
            const components = item.components || {};
            
            // Valence edge
            if (components.valence !== undefined) {
                edges.push({
                    from: 'm_valence',
                    to: `a_${item.archetype}`,
                    width: Math.max(0.5, components.valence * 3),
                    color: { color: COLORS.valence, opacity: 0.3 + components.valence * 0.5 },
                    smooth: { type: 'cubicBezier', roundness: 0.4 },
                });
            }
            
            // Tension edge
            if (components.tension !== undefined) {
                edges.push({
                    from: 'm_tension',
                    to: `a_${item.archetype}`,
                    width: Math.max(0.5, components.tension * 3),
                    color: { color: COLORS.tension, opacity: 0.3 + components.tension * 0.5 },
                    smooth: { type: 'cubicBezier', roundness: 0.4 },
                });
            }
            
            // Hope edge
            if (components.hope !== undefined) {
                edges.push({
                    from: 'm_hope',
                    to: `a_${item.archetype}`,
                    width: Math.max(0.5, components.hope * 3),
                    color: { color: COLORS.hope, opacity: 0.3 + components.hope * 0.5 },
                    smooth: { type: 'cubicBezier', roundness: 0.4 },
                });
            }
            
            // Energy edge
            if (components.energy !== undefined) {
                edges.push({
                    from: 'm_energy',
                    to: `a_${item.archetype}`,
                    width: Math.max(0.5, components.energy * 3),
                    color: { color: COLORS.energy, opacity: 0.3 + components.energy * 0.5 },
                    smooth: { type: 'cubicBezier', roundness: 0.4 },
                });
            }
        });
        
        // Create network
        const network = new vis.Network(container, { nodes, edges }, {
            physics: false,
            interaction: {
                dragNodes: false,
                dragView: true,
                zoomView: true,
                hover: true,
                tooltipDelay: 100,
            },
            nodes: {
                margin: 10,
            },
            edges: {
                selectionWidth: 2,
            },
        });
        
        // Fit to view
        network.once('afterDrawing', () => {
            network.fit({ animation: false });
        });
    }
    
    // =============================================================================
    // VIZ 2: ARCHETYPE → PROMPT ASSEMBLY
    // =============================================================================
    
    function buildPromptAssemblyGraph(data) {
        const container = document.getElementById('graph-prompt-assembly');
        if (!container) return;
        
        const nodes = [];
        const edges = [];
        
        const selection = data.selection;
        const archetypes = data.archetypes || {};
        const prompt = data.prompt || {};
        const components = prompt.components || {};
        
        const primary = selection.primary;
        const secondary = selection.secondary;
        const blendRatio = selection.blend_ratio || 1;
        
        const primaryData = archetypes[primary] || {};
        const secondaryData = secondary ? archetypes[secondary] : null;
        
        const primaryDesc = primaryData.descriptor || {};
        const secondaryDesc = secondaryData ? secondaryData.descriptor : null;
        
        // Primary archetype node
        nodes.push({
            id: 'primary',
            label: `${primary?.replace(/_/g, ' ') || 'Primary'}\n(${Math.round(blendRatio * 100)}%)`,
            x: -200,
            y: -80,
            fixed: true,
            shape: 'box',
            color: {
                background: COLORS.node,
                border: COLORS.primary,
                highlight: { background: COLORS.nodeHighlight, border: COLORS.primary },
            },
            font: { color: COLORS.text, size: 11, face: 'IBM Plex Mono, monospace' },
            borderWidth: 3,
        });
        
        // Secondary archetype node
        if (secondary) {
            nodes.push({
                id: 'secondary',
                label: `${secondary.replace(/_/g, ' ')}\n(${Math.round((1 - blendRatio) * 100)}%)`,
                x: -200,
                y: 80,
                fixed: true,
                shape: 'box',
                color: {
                    background: COLORS.node,
                    border: COLORS.secondary,
                    highlight: { background: COLORS.nodeHighlight, border: COLORS.secondary },
                },
                font: { color: COLORS.textDim, size: 11, face: 'IBM Plex Mono, monospace' },
                borderWidth: 2,
            });
        }
        
        // Component nodes (middle)
        const usedComponents = [
            { id: 'c_genre', label: `Genre\n${components.genre || '?'}`, x: 0, y: -120, color: COLORS.genre },
            { id: 'c_instruments', label: `Instruments\n${(components.instruments || []).slice(0, 2).join(', ')}${components.instruments?.length > 2 ? '...' : ''}`, x: 0, y: -40, color: COLORS.instruments },
            { id: 'c_moods', label: `Moods\n${(components.moods || []).join(', ')}`, x: 0, y: 40, color: COLORS.moods },
            { id: 'c_tempo', label: `Tempo\n${components.tempo || '?'} BPM`, x: 0, y: 120, color: COLORS.tempo },
        ];
        
        usedComponents.forEach(c => {
            nodes.push({
                id: c.id,
                label: c.label,
                x: c.x,
                y: c.y,
                fixed: true,
                shape: 'box',
                color: {
                    background: COLORS.node,
                    border: c.color,
                    highlight: { background: COLORS.nodeHighlight, border: c.color },
                },
                font: { color: COLORS.text, size: 10, face: 'IBM Plex Mono, monospace', multi: true },
                borderWidth: 1,
            });
        });
        
        // Final prompt node (right)
        const promptPreview = (prompt.final_prompt || '').slice(0, 40) + '...';
        nodes.push({
            id: 'final_prompt',
            label: `Final Prompt\n"${promptPreview}"`,
            x: 220,
            y: 0,
            fixed: true,
            shape: 'box',
            color: {
                background: '#1a1a2e',
                border: '#6366f1',
                highlight: { background: '#252540', border: '#8b8bf0' },
            },
            font: { color: COLORS.text, size: 10, face: 'IBM Plex Mono, monospace' },
            borderWidth: 2,
        });
        
        // Edges: Primary → Components
        // Determine which came from primary (simplified - assume most from primary)
        edges.push({ from: 'primary', to: 'c_genre', width: 2, color: { color: COLORS.primary, opacity: 0.6 }, smooth: { type: 'cubicBezier' } });
        edges.push({ from: 'primary', to: 'c_instruments', width: 2, color: { color: COLORS.primary, opacity: 0.6 }, smooth: { type: 'cubicBezier' } });
        edges.push({ from: 'primary', to: 'c_moods', width: 2, color: { color: COLORS.primary, opacity: 0.6 }, smooth: { type: 'cubicBezier' } });
        edges.push({ from: 'primary', to: 'c_tempo', width: 2, color: { color: COLORS.primary, opacity: 0.6 }, smooth: { type: 'cubicBezier' } });
        
        // Edges: Secondary → Components (if applicable)
        if (secondary) {
            // Secondary contributes some instruments
            edges.push({ from: 'secondary', to: 'c_instruments', width: 1.5, color: { color: COLORS.secondary, opacity: 0.5 }, smooth: { type: 'cubicBezier' }, dashes: true });
            edges.push({ from: 'secondary', to: 'c_moods', width: 1, color: { color: COLORS.secondary, opacity: 0.4 }, smooth: { type: 'cubicBezier' }, dashes: true });
        }
        
        // Edges: Components → Final Prompt
        usedComponents.forEach(c => {
            edges.push({
                from: c.id,
                to: 'final_prompt',
                width: 1.5,
                color: { color: c.color, opacity: 0.5 },
                smooth: { type: 'cubicBezier', roundness: 0.3 },
                arrows: { to: { enabled: true, scaleFactor: 0.5 } },
            });
        });
        
        // Create network
        const network = new vis.Network(container, { nodes, edges }, {
            physics: false,
            interaction: {
                dragNodes: false,
                dragView: true,
                zoomView: true,
                hover: true,
                tooltipDelay: 100,
            },
            nodes: {
                margin: 10,
            },
        });
        
        // Fit to view
        network.once('afterDrawing', () => {
            network.fit({ animation: false });
        });
    }
    
});
