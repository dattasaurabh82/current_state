/**
 * Derivation Visualization - Full Flow
 * 
 * Complete flow:
 * NEWS SCRAPING → STRUCTURED OUTPUT → METRICS → ARCHETYPES → PROMPT ASSEMBLY → FINAL PROMPT
 *                                                                ↑              ↑
 *                                                             THEMES        DATE SEED
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // =============================================================================
    // DRACULA COLOR PALETTE
    // =============================================================================
    
    const COLORS = {
        // Background
        bg: '#282a36',
        bgDark: '#1e1f29',
        bgLight: '#343746',
        
        // Text
        text: '#f8f8f2',
        textDim: '#6272a4',
        
        // Dracula accent colors
        cyan: '#8be9fd',
        green: '#50fa7b',
        orange: '#ffb86c',
        pink: '#ff79c6',
        purple: '#bd93f9',
        red: '#ff5555',
        yellow: '#f1fa8c',
        
        // Node backgrounds - transparent
        nodeBg: 'transparent',
        nodeHighlight: 'rgba(68, 71, 90, 0.5)',
        
        // Edges
        edge: '#44475a',
        edgeHighlight: '#6272a4',
    };
    
    // =============================================================================
    // SHARED SETTINGS
    // =============================================================================
    
    const NODE_WIDTH = 140;
    const NODE_FONT = { 
        color: COLORS.text, 
        size: 10, 
        face: 'IBM Plex Mono, monospace',
        multi: 'html',
    };
    const EDGE_SMOOTH = { type: 'cubicBezier', roundness: 0.4 };
    
    // =============================================================================
    // NETWORK INSTANCE & POSITIONS
    // =============================================================================
    
    let network = null;
    let initialPositions = {};
    
    // =============================================================================
    // HELPER: Create node
    // =============================================================================
    
    function createNode(id, label, x, y, borderColor, options = {}) {
        const node = {
            id,
            label,
            x,
            y,
            shape: 'box',
            color: { 
                background: COLORS.nodeBg, 
                border: borderColor, 
                highlight: { background: COLORS.nodeHighlight, border: borderColor },
                hover: { background: COLORS.nodeHighlight, border: borderColor },
            },
            font: { ...NODE_FONT, align: options.align || 'center' },
            borderWidth: 1,
            widthConstraint: { minimum: NODE_WIDTH, maximum: NODE_WIDTH },
            margin: 10,
            ...options,
        };
        
        initialPositions[id] = { x, y };
        return node;
    }
    
    // =============================================================================
    // HELPER: Create edge
    // =============================================================================
    
    function createEdge(from, to, color, options = {}) {
        const { arrows, dashes, width, opacity, ...rest } = options;
        return {
            from,
            to,
            width: width || 1.5,
            color: { color, opacity: opacity || 0.7, highlight: color, hover: color },
            smooth: EDGE_SMOOTH,
            arrows: arrows ? { to: { enabled: true, scaleFactor: 0.4 } } : undefined,
            dashes: dashes || false,
            ...rest,
        };
    }
    
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
        
        // Data extraction
        const news = data.news || {};
        const summary = data.summary || '';
        const metrics = data.input_metrics || {};
        const selection = data.selection || {};
        const allScores = selection.all_scores || [];
        const prompt = data.prompt || {};
        const components = prompt.components || {};
        const themes = data.themes || [];
        const dateSeed = data.date || '2026-01-09';
        
        const primary = selection.primary;
        const secondary = selection.secondary;
        
        // X positions for columns
        const X = {
            news: -650,
            structured: -480,
            metrics: -310,
            archetypes: -100,
            middle: 100,
            layers: 280,
            finalPrompt: 480,
        };
        
        // ---------------------------------------------------------------------
        // COLUMN 0: NEWS SCRAPING
        // ---------------------------------------------------------------------
        
        const articleCount = news.total_articles || 0;
        const regions = (news.regions || []).join(', ');
        const newsLabel = `NEWS SCRAPING\n\n${articleCount} ARTICLES\n${(news.regions || []).length} REGIONS`;
        
        // Build tooltip with sample headlines
        let newsTooltip = `NEWS SCRAPING\n`;
        newsTooltip += `────────────────────\n`;
        newsTooltip += `Total: ${articleCount} articles\n`;
        newsTooltip += `Regions: ${regions}\n\n`;
        newsTooltip += `SAMPLE HEADLINES:\n`;
        (news.sample_headlines || []).slice(0, 5).forEach(h => {
            newsTooltip += `• ${h.title}\n  [${h.source}]\n`;
        });
        
        nodes.push(createNode('news_scraping', newsLabel, X.news, 0, COLORS.cyan, {
            title: newsTooltip,
        }));
        
        // ---------------------------------------------------------------------
        // COLUMN 1: STRUCTURED OUTPUT
        // ---------------------------------------------------------------------
        
        const structuredLabel = `STRUCTURED OUTPUT\n\nVAL: ${metrics.valence >= 0 ? '+' : ''}${(metrics.valence || 0).toFixed(2)}\nTEN: ${(metrics.tension || 0).toFixed(2)}\nHOP: ${(metrics.hope || 0).toFixed(2)}\nENE: ${(metrics.energy || 'MED').toString().toUpperCase().slice(0, 3)}`;
        
        let structuredTooltip = `STRUCTURED OUTPUT\n`;
        structuredTooltip += `────────────────────\n`;
        structuredTooltip += `Emotional Valence: ${(metrics.valence || 0).toFixed(3)}\n`;
        structuredTooltip += `Tension Level: ${(metrics.tension || 0).toFixed(3)}\n`;
        structuredTooltip += `Hope Factor: ${(metrics.hope || 0).toFixed(3)}\n`;
        structuredTooltip += `Energy Level: ${metrics.energy || 'medium'}\n\n`;
        structuredTooltip += `THEMES: ${themes.join(', ')}\n\n`;
        structuredTooltip += `SUMMARY:\n${summary}`;
        
        nodes.push(createNode('structured_output', structuredLabel, X.structured, 0, COLORS.purple, {
            title: structuredTooltip,
        }));
        
        // Edge: News → Structured
        edges.push(createEdge('news_scraping', 'structured_output', COLORS.cyan, { arrows: true }));
        
        // ---------------------------------------------------------------------
        // COLUMN 2: METRICS
        // ---------------------------------------------------------------------
        
        const metricDefs = [
            { id: 'metric_valence', label: `VALENCE\n${metrics.valence >= 0 ? '+' : ''}${(metrics.valence || 0).toFixed(2)}`, color: COLORS.green, y: -100 },
            { id: 'metric_tension', label: `TENSION\n${(metrics.tension || 0).toFixed(2)}`, color: COLORS.red, y: -33 },
            { id: 'metric_hope', label: `HOPE\n${(metrics.hope || 0).toFixed(2)}`, color: COLORS.cyan, y: 33 },
            { id: 'metric_energy', label: `ENERGY\n${(metrics.energy || 'MEDIUM').toString().toUpperCase()}`, color: COLORS.yellow, y: 100 },
        ];
        
        metricDefs.forEach(m => {
            nodes.push(createNode(m.id, m.label, X.metrics, m.y, m.color));
        });
        
        // Edges: Structured → Metrics
        metricDefs.forEach(m => {
            edges.push(createEdge('structured_output', m.id, COLORS.purple, { 
                arrows: true,
                opacity: 0.5,
            }));
        });
        
        // ---------------------------------------------------------------------
        // COLUMN 3: ARCHETYPES
        // ---------------------------------------------------------------------
        
        const archetypeYStart = -150;
        const archetypeYStep = 60;
        
        allScores.forEach((item, i) => {
            const isPrimary = item.archetype === primary;
            const isSecondary = item.archetype === secondary;
            
            let borderColor = COLORS.textDim;
            if (isPrimary) borderColor = COLORS.pink;
            else if (isSecondary) borderColor = COLORS.orange;
            
            const displayName = item.archetype.replace(/_/g, ' ').toUpperCase();
            const scorePercent = Math.round(item.score * 100);
            const marker = isPrimary ? ' ★' : (isSecondary ? ' ○' : '');
            
            const y = archetypeYStart + (i * archetypeYStep);
            
            // Tooltip with score breakdown
            const comps = item.components || {};
            let archTooltip = `${displayName}\n`;
            archTooltip += `────────────────────\n`;
            archTooltip += `Total Score: ${(item.score * 100).toFixed(1)}%\n\n`;
            archTooltip += `COMPONENT SCORES:\n`;
            archTooltip += `• Valence: ${((comps.valence || 0) * 100).toFixed(0)}%\n`;
            archTooltip += `• Tension: ${((comps.tension || 0) * 100).toFixed(0)}%\n`;
            archTooltip += `• Hope: ${((comps.hope || 0) * 100).toFixed(0)}%\n`;
            archTooltip += `• Energy: ${((comps.energy || 0) * 100).toFixed(0)}%\n`;
            
            nodes.push(createNode(
                `arch_${item.archetype}`,
                `${displayName}${marker}\n${scorePercent}%`,
                X.archetypes,
                y,
                borderColor,
                { 
                    title: archTooltip,
                    font: { 
                        ...NODE_FONT, 
                        color: isPrimary || isSecondary ? COLORS.text : COLORS.textDim,
                    },
                }
            ));
            
            // Edges: Metrics → Archetype (weighted by component scores)
            if (comps.valence !== undefined && comps.valence > 0.3) {
                edges.push(createEdge('metric_valence', `arch_${item.archetype}`, COLORS.green, {
                    opacity: 0.2 + comps.valence * 0.4,
                }));
            }
            if (comps.tension !== undefined && comps.tension > 0.3) {
                edges.push(createEdge('metric_tension', `arch_${item.archetype}`, COLORS.red, {
                    opacity: 0.2 + comps.tension * 0.4,
                }));
            }
            if (comps.hope !== undefined && comps.hope > 0.3) {
                edges.push(createEdge('metric_hope', `arch_${item.archetype}`, COLORS.cyan, {
                    opacity: 0.2 + comps.hope * 0.4,
                }));
            }
            if (comps.energy !== undefined && comps.energy > 0.3) {
                edges.push(createEdge('metric_energy', `arch_${item.archetype}`, COLORS.yellow, {
                    opacity: 0.2 + comps.energy * 0.4,
                }));
            }
        });
        
        // ---------------------------------------------------------------------
        // COLUMN 4 TOP: THEMES
        // ---------------------------------------------------------------------
        
        const themesLabel = `THEMES\n\n• ${themes.map(t => t.toUpperCase()).join('\n• ')}`;
        
        nodes.push(createNode('themes', themesLabel, X.middle, -100, COLORS.pink, {
            align: 'left',
            title: `DOMINANT THEMES\n────────────────────\nExtracted from news analysis:\n• ${themes.join('\n• ')}`,
        }));
        
        // ---------------------------------------------------------------------
        // COLUMN 4 BOTTOM: DATE SEED
        // ---------------------------------------------------------------------
        
        const instrumentVariant = components.instrument_variant ?? 0;
        const dateSeedLabel = `DATE SEED\n\n${dateSeed}\nVARIANT: ${instrumentVariant}`;
        
        nodes.push(createNode('date_seed', dateSeedLabel, X.middle, 100, COLORS.orange, {
            title: `DATE SEED\n────────────────────\nDate: ${dateSeed}\nInstrument Variant: ${instrumentVariant}\n\nUsed for reproducible\nrandomization in prompt\ngeneration.`,
        }));
        
        // ---------------------------------------------------------------------
        // COLUMN 5: PROMPT ASSEMBLY LAYERS
        // ---------------------------------------------------------------------
        
        // Layer 1: STRUCTURE
        const genre = (components.genre || 'AMBIENT').toUpperCase();
        const instruments = (components.instruments || []).map(i => i.toUpperCase()).slice(0, 3);
        const moods = (components.moods || []).map(m => m.toUpperCase()).slice(0, 3);
        const tempo = components.tempo || 70;
        
        const layer1Label = `LAYER 1: STRUCTURE\n\nGENRE: ${genre}\nTEMPO: ${tempo} BPM`;
        
        let layer1Tooltip = `LAYER 1: STRUCTURE\n`;
        layer1Tooltip += `(From Archetypes)\n`;
        layer1Tooltip += `────────────────────\n`;
        layer1Tooltip += `Genre: ${genre}\n`;
        layer1Tooltip += `Instruments: ${instruments.join(', ')}\n`;
        layer1Tooltip += `Moods: ${moods.join(', ')}\n`;
        layer1Tooltip += `Tempo: ${tempo} BPM`;
        
        nodes.push(createNode('layer_structure', layer1Label, X.layers, -100, COLORS.purple, {
            title: layer1Tooltip,
            align: 'left',
        }));
        
        // Layer 2: COLOR
        const texTimbre = (components.texture_timbre || []).map(t => t.toUpperCase());
        const texMovement = (components.texture_movement || []).map(t => t.toUpperCase());
        const texHarmonic = (components.texture_harmonic || []).map(t => t.toUpperCase());
        
        const layer2Label = `LAYER 2: COLOR\n\nTIMBRE: ${texTimbre.slice(0, 2).join(', ')}\nMOVE: ${texMovement.slice(0, 1).join(', ')}`;
        
        let layer2Tooltip = `LAYER 2: COLOR\n`;
        layer2Tooltip += `(From Theme Textures)\n`;
        layer2Tooltip += `────────────────────\n`;
        layer2Tooltip += `Timbre: ${texTimbre.join(', ')}\n`;
        layer2Tooltip += `Movement: ${texMovement.join(', ')}\n`;
        layer2Tooltip += `Harmonic: ${texHarmonic.join(', ')}`;
        
        nodes.push(createNode('layer_color', layer2Label, X.layers, 0, COLORS.pink, {
            title: layer2Tooltip,
            align: 'left',
        }));
        
        // Layer 3: VARIETY
        const layer3Label = `LAYER 3: VARIETY\n\nVARIANT: ${instrumentVariant}\nTEMPO ADJ: ±3`;
        
        nodes.push(createNode('layer_variety', layer3Label, X.layers, 100, COLORS.orange, {
            title: `LAYER 3: VARIETY\n(From Date Seed)\n────────────────────\nInstrument Variant: ${instrumentVariant}\nTempo Adjustment: ±3 BPM\n\nAdds variation based on\ndate-seeded randomization.`,
            align: 'left',
        }));
        
        // ---------------------------------------------------------------------
        // COLUMN 6: FINAL PROMPT
        // ---------------------------------------------------------------------
        
        const finalPromptText = (prompt.final_prompt || '').toUpperCase().slice(0, 50) + '...';
        const finalPromptLabel = `FINAL PROMPT\n\n"${finalPromptText}"`;
        
        nodes.push(createNode('final_prompt', finalPromptLabel, X.finalPrompt, 0, COLORS.green, {
            title: `FINAL PROMPT\n────────────────────\n${prompt.final_prompt || ''}`,
        }));
        
        // ---------------------------------------------------------------------
        // EDGES: ARCHETYPES → LAYER 1
        // ---------------------------------------------------------------------
        
        if (primary) {
            edges.push(createEdge(`arch_${primary}`, 'layer_structure', COLORS.pink, {
                arrows: true,
                width: 2,
            }));
        }
        
        if (secondary) {
            edges.push(createEdge(`arch_${secondary}`, 'layer_structure', COLORS.orange, {
                arrows: true,
                dashes: [5, 5],
                opacity: 0.5,
            }));
        }
        
        // ---------------------------------------------------------------------
        // EDGES: THEMES → LAYER 2
        // ---------------------------------------------------------------------
        
        edges.push(createEdge('themes', 'layer_color', COLORS.pink, { arrows: true }));
        
        // ---------------------------------------------------------------------
        // EDGES: DATE SEED → LAYER 3
        // ---------------------------------------------------------------------
        
        edges.push(createEdge('date_seed', 'layer_variety', COLORS.orange, { arrows: true }));
        
        // ---------------------------------------------------------------------
        // EDGES: ALL LAYERS → FINAL PROMPT
        // ---------------------------------------------------------------------
        
        edges.push(createEdge('layer_structure', 'final_prompt', COLORS.purple, { arrows: true }));
        edges.push(createEdge('layer_color', 'final_prompt', COLORS.pink, { arrows: true }));
        edges.push(createEdge('layer_variety', 'final_prompt', COLORS.orange, { arrows: true }));
        
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
                tooltipDelay: 200,
                selectConnectedEdges: true,
                navigationButtons: false,
                keyboard: {
                    enabled: true,
                    speed: { x: 10, y: 10, zoom: 0.02 },
                    bindToWindow: false,
                },
            },
            nodes: {
                shadow: {
                    enabled: true,
                    color: 'rgba(0,0,0,0.5)',
                    size: 8,
                    x: 3,
                    y: 3,
                },
            },
            edges: {
                selectionWidth: 2,
            },
        };
        
        network = new vis.Network(container, { nodes, edges }, options);
        
        // Enable focus on container for keyboard nav
        container.tabIndex = 0;
        
        // Fit to view after drawing
        network.once('afterDrawing', () => {
            network.fit({ 
                animation: { duration: 300, easingFunction: 'easeInOutQuad' },
            });
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
    
    initFullFlowGraph();
    
});
