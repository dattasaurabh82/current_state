/**
 * Derivation Visualization - Full Flow
 * 
 * Single unified canvas showing:
 * METRICS → ARCHETYPES → PROMPT ASSEMBLY (3 layers) → FINAL PROMPT
 *                              ↑                ↑
 *                           THEMES          DATE SEED
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // =============================================================================
    // COLORS
    // =============================================================================
    
    const COLORS = {
        bg: '#0a0a0a',
        node: '#1a1a1a',
        nodeBorder: '#333333',
        nodeHighlight: '#444444',
        text: '#e0e0e0',
        textDim: '#808080',
        edge: '#404040',
        
        // Metric colors
        valence: '#66cc66',
        tension: '#cc6666',
        hope: '#6699cc',
        energy: '#cccc66',
        
        // Archetype colors
        primary: '#ffffff',
        secondary: '#a0a0a0',
        inactive: '#505050',
        
        // Layer colors
        structure: '#8888cc',
        color: '#cc8888',
        variety: '#88cc88',
        
        // Other
        themes: '#cc88cc',
        dateSeed: '#88cccc',
        finalPrompt: '#cccc88',
    };
    
    // =============================================================================
    // NETWORK INSTANCE & POSITIONS
    // =============================================================================
    
    let network = null;
    let initialPositions = {};
    
    // =============================================================================
    // FETCH DATA & BUILD
    // =============================================================================
    
    async function initFullFlowGraph() {
        try {
            const response = await fetch('/api/derivation');
            const data = await response.json();
            
            if (data.error) {
                console.error('[Derivation] Error:', data.error);
                return;
            }
            
            buildFullFlowGraph(data);
            
        } catch (e) {
            console.error('[Derivation] Failed to load data:', e);
        }
    }
    
    // =============================================================================
    // BUILD FULL FLOW GRAPH
    // =============================================================================
    
    function buildFullFlowGraph(data) {
        const container = document.getElementById('graph-full-flow');
        if (!container) return;
        
        const nodes = [];
        const edges = [];
        
        const metrics = data.input_metrics || {};
        const selection = data.selection || {};
        const allScores = selection.all_scores || [];
        const archetypes = data.archetypes || {};
        const prompt = data.prompt || {};
        const components = prompt.components || {};
        
        const primary = selection.primary;
        const secondary = selection.secondary;
        
        // X positions for columns
        const X = {
            metrics: -500,
            archetypes: -200,
            themes: 50,
            layers: 250,
            finalPrompt: 500,
        };
        
        // ---------------------------------------------------------------------
        // COLUMN 1: METRICS
        // ---------------------------------------------------------------------
        
        const metricDefs = [
            { id: 'metric_valence', label: `VALENCE\n${metrics.valence >= 0 ? '+' : ''}${(metrics.valence || 0).toFixed(2)}`, color: COLORS.valence, y: -120 },
            { id: 'metric_tension', label: `TENSION\n${(metrics.tension || 0).toFixed(2)}`, color: COLORS.tension, y: -40 },
            { id: 'metric_hope', label: `HOPE\n${(metrics.hope || 0).toFixed(2)}`, color: COLORS.hope, y: 40 },
            { id: 'metric_energy', label: `ENERGY\n${(metrics.energy || 'MEDIUM').toUpperCase()}`, color: COLORS.energy, y: 120 },
        ];
        
        metricDefs.forEach(m => {
            nodes.push({
                id: m.id,
                label: m.label,
                x: X.metrics,
                y: m.y,
                shape: 'box',
                color: { background: COLORS.node, border: m.color, highlight: { background: COLORS.nodeHighlight, border: m.color } },
                font: { color: COLORS.text, size: 11, face: 'IBM Plex Mono, monospace', multi: 'html' },
                borderWidth: 2,
                widthConstraint: { minimum: 100, maximum: 100 },
            });
            initialPositions[m.id] = { x: X.metrics, y: m.y };
        });
        
        // ---------------------------------------------------------------------
        // COLUMN 2: ARCHETYPES
        // ---------------------------------------------------------------------
        
        const archetypeYStart = -150;
        const archetypeYStep = 60;
        
        allScores.forEach((item, i) => {
            const isPrimary = item.archetype === primary;
            const isSecondary = item.archetype === secondary;
            
            let borderColor = COLORS.inactive;
            let borderWidth = 1;
            let fontColor = COLORS.textDim;
            
            if (isPrimary) {
                borderColor = COLORS.primary;
                borderWidth = 3;
                fontColor = COLORS.text;
            } else if (isSecondary) {
                borderColor = COLORS.secondary;
                borderWidth = 2;
                fontColor = COLORS.text;
            }
            
            const displayName = item.archetype.replace(/_/g, ' ').toUpperCase();
            const scorePercent = Math.round(item.score * 100);
            const marker = isPrimary ? ' ★' : (isSecondary ? ' ○' : '');
            
            const y = archetypeYStart + (i * archetypeYStep);
            
            nodes.push({
                id: `arch_${item.archetype}`,
                label: `${displayName}${marker}\n${scorePercent}%`,
                x: X.archetypes,
                y: y,
                shape: 'box',
                color: { background: COLORS.node, border: borderColor, highlight: { background: COLORS.nodeHighlight, border: borderColor } },
                font: { color: fontColor, size: 10, face: 'IBM Plex Mono, monospace', multi: 'html' },
                borderWidth: borderWidth,
                widthConstraint: { minimum: 130, maximum: 130 },
            });
            initialPositions[`arch_${item.archetype}`] = { x: X.archetypes, y: y };
            
            // Edges: Metrics → This Archetype
            const comps = item.components || {};
            
            if (comps.valence !== undefined) {
                edges.push({
                    from: 'metric_valence', to: `arch_${item.archetype}`,
                    width: Math.max(0.5, comps.valence * 2.5),
                    color: { color: COLORS.valence, opacity: 0.2 + comps.valence * 0.4 },
                    smooth: { type: 'cubicBezier', roundness: 0.3 },
                });
            }
            if (comps.tension !== undefined) {
                edges.push({
                    from: 'metric_tension', to: `arch_${item.archetype}`,
                    width: Math.max(0.5, comps.tension * 2.5),
                    color: { color: COLORS.tension, opacity: 0.2 + comps.tension * 0.4 },
                    smooth: { type: 'cubicBezier', roundness: 0.3 },
                });
            }
            if (comps.hope !== undefined) {
                edges.push({
                    from: 'metric_hope', to: `arch_${item.archetype}`,
                    width: Math.max(0.5, comps.hope * 2.5),
                    color: { color: COLORS.hope, opacity: 0.2 + comps.hope * 0.4 },
                    smooth: { type: 'cubicBezier', roundness: 0.3 },
                });
            }
            if (comps.energy !== undefined) {
                edges.push({
                    from: 'metric_energy', to: `arch_${item.archetype}`,
                    width: Math.max(0.5, comps.energy * 2.5),
                    color: { color: COLORS.energy, opacity: 0.2 + comps.energy * 0.4 },
                    smooth: { type: 'cubicBezier', roundness: 0.3 },
                });
            }
        });
        
        // ---------------------------------------------------------------------
        // COLUMN 3 TOP: THEMES
        // ---------------------------------------------------------------------
        
        // Get themes from API data
        let themesList = data.themes || components.source_themes || ['POLITICS', 'ECONOMY', 'TECHNOLOGY'];
        
        if (!themesList || themesList.length === 0) {
            themesList = ['POLITICS', 'ECONOMY', 'TECHNOLOGY'];
        }
        
        const themesLabel = `THEMES\n• ${themesList.map(t => t.toUpperCase()).join('\n• ')}`;
        
        nodes.push({
            id: 'themes',
            label: themesLabel,
            x: X.themes,
            y: -140,
            shape: 'box',
            color: { background: COLORS.node, border: COLORS.themes, highlight: { background: COLORS.nodeHighlight, border: COLORS.themes } },
            font: { color: COLORS.text, size: 10, face: 'IBM Plex Mono, monospace', multi: 'html', align: 'left' },
            borderWidth: 2,
            widthConstraint: { minimum: 120, maximum: 120 },
        });
        initialPositions['themes'] = { x: X.themes, y: -140 };
        
        // ---------------------------------------------------------------------
        // COLUMN 3 BOTTOM: DATE SEED
        // ---------------------------------------------------------------------
        
        const dateSeed = data.date || '2026-01-09';
        const instrumentVariant = components.instrument_variant ?? 0;
        
        nodes.push({
            id: 'date_seed',
            label: `DATE SEED\n${dateSeed}\nVARIANT: ${instrumentVariant}`,
            x: X.themes,
            y: 140,
            shape: 'box',
            color: { background: COLORS.node, border: COLORS.dateSeed, highlight: { background: COLORS.nodeHighlight, border: COLORS.dateSeed } },
            font: { color: COLORS.text, size: 10, face: 'IBM Plex Mono, monospace', multi: 'html' },
            borderWidth: 2,
            widthConstraint: { minimum: 120, maximum: 120 },
        });
        initialPositions['date_seed'] = { x: X.themes, y: 140 };
        
        // ---------------------------------------------------------------------
        // COLUMN 4: PROMPT ASSEMBLY LAYERS
        // ---------------------------------------------------------------------
        
        // Layer 1: STRUCTURE (from Archetypes)
        const genre = (components.genre || 'AMBIENT').toUpperCase();
        const instruments = (components.instruments || []).map(i => i.toUpperCase()).slice(0, 3);
        const moods = (components.moods || []).map(m => m.toUpperCase()).slice(0, 3);
        const tempo = components.tempo || 70;
        
        const layer1Label = `LAYER 1: STRUCTURE\n(FROM ARCHETYPES)\n\n• GENRE: ${genre}\n• INSTR: ${instruments.join(', ')}\n• MOODS: ${moods.join(', ')}\n• TEMPO: ${tempo} BPM`;
        
        nodes.push({
            id: 'layer_structure',
            label: layer1Label,
            x: X.layers,
            y: -120,
            shape: 'box',
            color: { background: COLORS.node, border: COLORS.structure, highlight: { background: COLORS.nodeHighlight, border: COLORS.structure } },
            font: { color: COLORS.text, size: 9, face: 'IBM Plex Mono, monospace', multi: 'html', align: 'left' },
            borderWidth: 2,
            widthConstraint: { minimum: 180, maximum: 180 },
        });
        initialPositions['layer_structure'] = { x: X.layers, y: -120 };
        
        // Layer 2: COLOR (from Theme Textures)
        const texTimbre = (components.texture_timbre || ['WOVEN', 'CLEAN']).map(t => t.toUpperCase());
        const texMovement = (components.texture_movement || ['SEQUENCED']).map(t => t.toUpperCase());
        const texHarmonic = (components.texture_harmonic || ['AMBIGUOUS']).map(t => t.toUpperCase());
        
        const layer2Label = `LAYER 2: COLOR\n(FROM THEME TEXTURES)\n\n• TIMBRE: ${texTimbre.join(', ')}\n• MOVEMENT: ${texMovement.join(', ')}\n• HARMONIC: ${texHarmonic.join(', ')}`;
        
        nodes.push({
            id: 'layer_color',
            label: layer2Label,
            x: X.layers,
            y: 20,
            shape: 'box',
            color: { background: COLORS.node, border: COLORS.color, highlight: { background: COLORS.nodeHighlight, border: COLORS.color } },
            font: { color: COLORS.text, size: 9, face: 'IBM Plex Mono, monospace', multi: 'html', align: 'left' },
            borderWidth: 2,
            widthConstraint: { minimum: 180, maximum: 180 },
        });
        initialPositions['layer_color'] = { x: X.layers, y: 20 };
        
        // Layer 3: VARIETY (from Date Seed)
        const layer3Label = `LAYER 3: VARIETY\n(FROM DATE SEED)\n\n• INSTR VARIANT: ${instrumentVariant}\n• TEMPO ADJUST: ±3\n• SEED SELECTION`;
        
        nodes.push({
            id: 'layer_variety',
            label: layer3Label,
            x: X.layers,
            y: 150,
            shape: 'box',
            color: { background: COLORS.node, border: COLORS.variety, highlight: { background: COLORS.nodeHighlight, border: COLORS.variety } },
            font: { color: COLORS.text, size: 9, face: 'IBM Plex Mono, monospace', multi: 'html', align: 'left' },
            borderWidth: 2,
            widthConstraint: { minimum: 180, maximum: 180 },
        });
        initialPositions['layer_variety'] = { x: X.layers, y: 150 };
        
        // ---------------------------------------------------------------------
        // COLUMN 5: FINAL PROMPT
        // ---------------------------------------------------------------------
        
        const finalPromptText = (prompt.final_prompt || '').toUpperCase().slice(0, 60) + '...';
        
        nodes.push({
            id: 'final_prompt',
            label: `FINAL PROMPT\n\n"${finalPromptText}"`,
            x: X.finalPrompt,
            y: 20,
            shape: 'box',
            color: { background: '#1a1a2e', border: COLORS.finalPrompt, highlight: { background: '#252540', border: COLORS.finalPrompt } },
            font: { color: COLORS.text, size: 10, face: 'IBM Plex Mono, monospace', multi: 'html' },
            borderWidth: 3,
            widthConstraint: { minimum: 180, maximum: 180 },
        });
        initialPositions['final_prompt'] = { x: X.finalPrompt, y: 20 };
        
        // ---------------------------------------------------------------------
        // EDGES: ARCHETYPES → LAYER 1
        // ---------------------------------------------------------------------
        
        if (primary) {
            edges.push({
                from: `arch_${primary}`, to: 'layer_structure',
                width: 3,
                color: { color: COLORS.primary, opacity: 0.8 },
                smooth: { type: 'cubicBezier', roundness: 0.2 },
                arrows: { to: { enabled: true, scaleFactor: 0.5 } },
            });
        }
        
        if (secondary) {
            edges.push({
                from: `arch_${secondary}`, to: 'layer_structure',
                width: 2,
                color: { color: COLORS.secondary, opacity: 0.5 },
                smooth: { type: 'cubicBezier', roundness: 0.2 },
                dashes: [5, 5],
                arrows: { to: { enabled: true, scaleFactor: 0.4 } },
            });
        }
        
        // ---------------------------------------------------------------------
        // EDGES: THEMES → LAYER 2
        // ---------------------------------------------------------------------
        
        edges.push({
            from: 'themes', to: 'layer_color',
            width: 2,
            color: { color: COLORS.themes, opacity: 0.7 },
            smooth: { type: 'cubicBezier', roundness: 0.2 },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        });
        
        // ---------------------------------------------------------------------
        // EDGES: DATE SEED → LAYER 3
        // ---------------------------------------------------------------------
        
        edges.push({
            from: 'date_seed', to: 'layer_variety',
            width: 2,
            color: { color: COLORS.dateSeed, opacity: 0.7 },
            smooth: { type: 'cubicBezier', roundness: 0.2 },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        });
        
        // ---------------------------------------------------------------------
        // EDGES: ALL LAYERS → FINAL PROMPT
        // ---------------------------------------------------------------------
        
        edges.push({
            from: 'layer_structure', to: 'final_prompt',
            width: 2,
            color: { color: COLORS.structure, opacity: 0.6 },
            smooth: { type: 'cubicBezier', roundness: 0.3 },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        });
        
        edges.push({
            from: 'layer_color', to: 'final_prompt',
            width: 2,
            color: { color: COLORS.color, opacity: 0.6 },
            smooth: { type: 'cubicBezier', roundness: 0.3 },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        });
        
        edges.push({
            from: 'layer_variety', to: 'final_prompt',
            width: 2,
            color: { color: COLORS.variety, opacity: 0.6 },
            smooth: { type: 'cubicBezier', roundness: 0.3 },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        });
        
        // ---------------------------------------------------------------------
        // CREATE NETWORK
        // ---------------------------------------------------------------------
        
        const options = {
            physics: false,
            interaction: {
                dragNodes: true,
                dragView: true,
                zoomView: true,
                hover: true,
                tooltipDelay: 100,
                selectConnectedEdges: true,
            },
            nodes: {
                margin: 10,
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.3)',
                    size: 5,
                    x: 2,
                    y: 2,
                },
            },
            edges: {
                selectionWidth: 2,
            },
        };
        
        network = new vis.Network(container, { nodes, edges }, options);
        
        // Fit to view after drawing
        network.once('afterDrawing', () => {
            network.fit({ animation: { duration: 300, easingFunction: 'easeInOutQuad' } });
        });
        
        // Setup reset button
        const resetBtn = document.getElementById('reset-layout-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', resetLayout);
        }
    }
    
    // =============================================================================
    // RESET LAYOUT
    // =============================================================================
    
    function resetLayout() {
        if (!network) return;
        
        // Move all nodes back to initial positions
        const updates = [];
        for (const [id, pos] of Object.entries(initialPositions)) {
            updates.push({ id, x: pos.x, y: pos.y });
        }
        
        network.body.data.nodes.update(updates);
        
        // Fit view
        setTimeout(() => {
            network.fit({ animation: { duration: 300, easingFunction: 'easeInOutQuad' } });
        }, 100);
    }
    
    // =============================================================================
    // INIT
    // =============================================================================
    
    // Initialize the graph
    initFullFlowGraph();
    
});
