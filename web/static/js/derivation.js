/**
 * Derivation Visualization - Pipeline Flow Graph
 * 
 * Interactive visualization of the news-to-music generation pipeline using vis-network.
 * 
 * Flow:
 * NEWS SCRAPING → STRUCTURED OUTPUT → METRICS → ARCHETYPES → LAYERS → FINAL PROMPT
 *                      ↓                                        ↑
 *                   THEMES ────────────────────────────────────┘
 *                                                                ↑
 *                   DATE SEED ──────────────────────────────────┘
 * 
 * @requires vis-network.js
 */

(function() {
    'use strict';

    // =========================================================================
    // Dracula Color Palette
    // =========================================================================

    const COLORS = Object.freeze({
        // Backgrounds
        bg: '#282a36',
        bgDark: '#1e1f29',
        bgLight: '#343746',
        
        // Text
        text: '#f8f8f2',
        textDim: '#6272a4',
        
        // Accent colors
        cyan: '#8be9fd',
        green: '#50fa7b',
        orange: '#ffb86c',
        pink: '#ff79c6',
        purple: '#bd93f9',
        red: '#ff5555',
        yellow: '#f1fa8c',
        
        // Node backgrounds
        nodeBg: '#0a0a0a',
        nodeHighlight: '#1a1a1a',
        
        // Edges
        edge: '#44475a',
        edgeHighlight: '#6272a4',
    });

    // =========================================================================
    // Configuration
    // =========================================================================

    /** Default node width in pixels */
    const NODE_WIDTH = 140;

    /** Font configuration for nodes */
    const NODE_FONT = Object.freeze({
        color: COLORS.text,
        size: 10,
        face: 'IBM Plex Mono, monospace',
        multi: 'html',
    });

    /** Edge smoothing configuration */
    const EDGE_SMOOTH = Object.freeze({
        type: 'cubicBezier',
        roundness: 0.4,
    });

    /** X positions for graph columns */
    const COLUMN_X = Object.freeze({
        news: -650,
        structured: -480,
        metrics: -310,
        archetypes: -100,
        middle: 100,
        layers: 280,
        finalPrompt: 480,
    });

    /** API endpoint for derivation data */
    const DERIVATION_API = '/api/derivation';

    // =========================================================================
    // State
    // =========================================================================

    /** @type {vis.Network|null} vis-network instance */
    let network = null;

    /** @type {Object.<string, {x: number, y: number}>} Initial node positions for reset */
    const initialPositions = {};

    // =========================================================================
    // Node & Edge Factories
    // =========================================================================

    /**
     * Create a node configuration object.
     * 
     * @param {string} id - Unique node identifier
     * @param {string} label - Display label (supports newlines)
     * @param {number} x - X position
     * @param {number} y - Y position
     * @param {string} borderColor - Border color (from COLORS)
     * @param {Object} options - Additional options (title, align, font, etc.)
     * @returns {Object} vis-network node configuration
     */
    function createNode(id, label, x, y, borderColor, options = {}) {
        // Store initial position for reset
        initialPositions[id] = { x, y };

        return {
            id,
            label,
            x,
            y,
            shape: 'box',
            shapeProperties: { borderRadius: 0 },
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
    }

    /**
     * Create an edge configuration object.
     * 
     * @param {string} from - Source node ID
     * @param {string} to - Target node ID
     * @param {string} color - Edge color
     * @param {Object} options - Additional options (arrows, dashes, width, opacity)
     * @returns {Object} vis-network edge configuration
     */
    function createEdge(from, to, color, options = {}) {
        const { arrows, dashes, width, opacity } = options;

        return {
            from,
            to,
            width: width || 1.5,
            color: {
                color,
                opacity: opacity || 0.7,
                highlight: color,
                hover: color,
            },
            smooth: EDGE_SMOOTH,
            arrows: arrows ? { to: { enabled: true, scaleFactor: 0.4 } } : undefined,
            dashes: dashes || false,
        };
    }

    // =========================================================================
    // Graph Building
    // =========================================================================

    /**
     * Build the news scraping node.
     */
    function buildNewsNode(nodes, edges, news) {
        const articleCount = news.total_articles || 0;
        const regionCount = (news.regions || []).length;
        const label = `NEWS SCRAPING\n\n${articleCount} ARTICLES\n${regionCount} REGIONS`;

        let tooltip = 'NEWS SCRAPING\n';
        tooltip += '──────────────────────────────────────────\n';
        tooltip += `Total: ${articleCount} articles\n`;
        tooltip += `Regions: ${(news.regions || []).join(', ')}\n`;
        tooltip += '──────────────────────────────────────────\n';
        tooltip += 'SAMPLE HEADLINES:\n';

        (news.sample_headlines || []).slice(0, 4).forEach(h => {
            const title = (h.title || '').slice(0, 40);
            tooltip += `• ${title}...\n  [${h.source}]\n`;
        });

        nodes.push(createNode('news_scraping', label, COLUMN_X.news, 0, COLORS.cyan, {
            title: tooltip,
        }));
    }

    /**
     * Build the structured output node.
     */
    function buildStructuredOutputNode(nodes, edges, metrics, themes, summary) {
        const valenceSign = (metrics.valence || 0) >= 0 ? '+' : '';
        const label = `STRUCTURED OUTPUT\n\nVAL: ${valenceSign}${(metrics.valence || 0).toFixed(2)}\n` +
                      `TEN: ${(metrics.tension || 0).toFixed(2)}\n` +
                      `HOP: ${(metrics.hope || 0).toFixed(2)}\n` +
                      `ENE: ${(metrics.energy || 'MED').toString().toUpperCase().slice(0, 3)}`;

        let tooltip = 'STRUCTURED OUTPUT\n';
        tooltip += '──────────────────────────────────────────\n';
        tooltip += `Valence: ${(metrics.valence || 0).toFixed(2)} | Tension: ${(metrics.tension || 0).toFixed(2)}\n`;
        tooltip += `Hope: ${(metrics.hope || 0).toFixed(2)} | Energy: ${metrics.energy || 'medium'}\n`;
        tooltip += '──────────────────────────────────────────\n';
        tooltip += `THEMES: ${themes.join(', ')}\n`;
        tooltip += '──────────────────────────────────────────\n';
        tooltip += summary;

        nodes.push(createNode('structured_output', label, COLUMN_X.structured, 0, COLORS.purple, {
            title: tooltip,
        }));

        edges.push(createEdge('news_scraping', 'structured_output', COLORS.cyan, { arrows: true }));
    }

    /**
     * Build the metric nodes.
     */
    function buildMetricNodes(nodes, edges, metrics) {
        const metricDefs = [
            { id: 'metric_valence', key: 'valence', label: 'VALENCE', color: COLORS.green, y: -100, signed: true },
            { id: 'metric_tension', key: 'tension', label: 'TENSION', color: COLORS.red, y: -33, signed: false },
            { id: 'metric_hope', key: 'hope', label: 'HOPE', color: COLORS.cyan, y: 33, signed: false },
            { id: 'metric_energy', key: 'energy', label: 'ENERGY', color: COLORS.yellow, y: 100, signed: false },
        ];

        metricDefs.forEach(m => {
            let value = metrics[m.key] || 0;
            let displayValue;

            if (m.key === 'energy') {
                displayValue = String(value).toUpperCase();
            } else {
                const sign = m.signed && value >= 0 ? '+' : '';
                displayValue = sign + value.toFixed(2);
            }

            nodes.push(createNode(m.id, `${m.label}\n${displayValue}`, COLUMN_X.metrics, m.y, m.color));
            edges.push(createEdge('structured_output', m.id, COLORS.purple, { arrows: true, opacity: 0.5 }));
        });
    }

    /**
     * Build the archetype nodes.
     */
    function buildArchetypeNodes(nodes, edges, allScores, primary, secondary) {
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

            // Build tooltip
            const comps = item.components || {};
            let tooltip = `${displayName}\n`;
            tooltip += '──────────────────────────────────────────\n';
            tooltip += `Total Score: ${(item.score * 100).toFixed(1)}%\n`;
            tooltip += '──────────────────────────────────────────\n';
            tooltip += `Val: ${((comps.valence || 0) * 100).toFixed(0)}% | `;
            tooltip += `Ten: ${((comps.tension || 0) * 100).toFixed(0)}%\n`;
            tooltip += `Hop: ${((comps.hope || 0) * 100).toFixed(0)}% | `;
            tooltip += `Ene: ${((comps.energy || 0) * 100).toFixed(0)}%`;

            const nodeId = `arch_${item.archetype}`;

            nodes.push(createNode(
                nodeId,
                `${displayName}${marker}\n${scorePercent}%`,
                COLUMN_X.archetypes,
                y,
                borderColor,
                {
                    title: tooltip,
                    font: {
                        ...NODE_FONT,
                        color: isPrimary || isSecondary ? COLORS.text : COLORS.textDim,
                    },
                }
            ));

            // Connect metrics to archetypes based on component scores
            const metricEdges = [
                { metric: 'metric_valence', component: 'valence', color: COLORS.green },
                { metric: 'metric_tension', component: 'tension', color: COLORS.red },
                { metric: 'metric_hope', component: 'hope', color: COLORS.cyan },
                { metric: 'metric_energy', component: 'energy', color: COLORS.yellow },
            ];

            metricEdges.forEach(({ metric, component, color }) => {
                const value = comps[component];
                if (value !== undefined && value > 0.3) {
                    edges.push(createEdge(metric, nodeId, color, {
                        opacity: 0.2 + value * 0.4,
                    }));
                }
            });
        });
    }

    /**
     * Build the themes node.
     */
    function buildThemesNode(nodes, edges, themes) {
        const themeList = themes.map(t => t.toUpperCase()).join('\n• ');
        const label = `THEMES\n\n• ${themeList}`;

        nodes.push(createNode('themes', label, COLUMN_X.middle, -100, COLORS.pink, {
            align: 'left',
            title: `DOMINANT THEMES\n──────────────────────────────────────────\n• ${themes.join(' • ')}`,
        }));

        edges.push(createEdge('structured_output', 'themes', COLORS.pink, { arrows: true, opacity: 0.5 }));
    }

    /**
     * Build the date seed node.
     */
    function buildDateSeedNode(nodes, edges, dateSeed, instrumentVariant) {
        const label = `DATE SEED\n\n${dateSeed}\nVARIANT: ${instrumentVariant}`;
        const tooltip = `DATE SEED\n──────────────────────────────────────────\n` +
                        `Date: ${dateSeed} | Variant: ${instrumentVariant}\n` +
                        `──────────────────────────────────────────\n` +
                        `Used for reproducible randomization`;

        nodes.push(createNode('date_seed', label, COLUMN_X.middle, 100, COLORS.orange, {
            title: tooltip,
        }));
    }

    /**
     * Build the layer nodes.
     */
    function buildLayerNodes(nodes, edges, components) {
        // Layer 1: Structure
        const genre = (components.genre || 'AMBIENT').toUpperCase();
        const tempo = components.tempo || 70;

        nodes.push(createNode('layer_structure', 
            `LAYER 1: STRUCTURE\n\nGENRE: ${genre}\nTEMPO: ${tempo} BPM`,
            COLUMN_X.layers, -100, COLORS.purple, {
                align: 'left',
                title: `LAYER 1: STRUCTURE (From Archetypes)\n──────────────────────────────────────────\n` +
                       `Genre: ${genre} | Tempo: ${tempo} BPM\n` +
                       `Instruments: ${(components.instruments || []).map(i => i.toUpperCase()).join(', ')}\n` +
                       `Moods: ${(components.moods || []).map(m => m.toUpperCase()).join(', ')}`,
            }
        ));

        // Layer 2: Color
        const texTimbre = (components.texture_timbre || []).map(t => t.toUpperCase());
        const texMovement = (components.texture_movement || []).map(t => t.toUpperCase());
        const texHarmonic = (components.texture_harmonic || []).map(t => t.toUpperCase());

        nodes.push(createNode('layer_color',
            `LAYER 2: COLOR\n\nTIMBRE: ${texTimbre.slice(0, 2).join(', ')}\nMOVE: ${texMovement.slice(0, 1).join(', ')}`,
            COLUMN_X.layers, 0, COLORS.pink, {
                align: 'left',
                title: `LAYER 2: COLOR (From Themes)\n──────────────────────────────────────────\n` +
                       `Timbre: ${texTimbre.join(', ')}\n` +
                       `Movement: ${texMovement.join(', ')}\n` +
                       `Harmonic: ${texHarmonic.join(', ')}`,
            }
        ));

        // Layer 3: Variety
        const variant = components.instrument_variant ?? 0;

        nodes.push(createNode('layer_variety',
            `LAYER 3: VARIETY\n\nVARIANT: ${variant}\nTEMPO ADJ: ±3`,
            COLUMN_X.layers, 100, COLORS.orange, {
                align: 'left',
                title: `LAYER 3: VARIETY (From Date Seed)\n──────────────────────────────────────────\n` +
                       `Variant: ${variant} | Tempo Adj: ±3 BPM`,
            }
        ));
    }

    /**
     * Build the final prompt node.
     */
    function buildFinalPromptNode(nodes, edges, prompt) {
        const promptText = (prompt.final_prompt || '').toUpperCase().slice(0, 50) + '...';
        const label = `FINAL PROMPT\n\n"${promptText}"`;

        nodes.push(createNode('final_prompt', label, COLUMN_X.finalPrompt, 0, COLORS.green, {
            title: `FINAL PROMPT\n──────────────────────────────────────────\n${(prompt.final_prompt || '').slice(0, 150)}...`,
        }));
    }

    /**
     * Build edges connecting layers to final prompt.
     */
    function buildLayerEdges(edges, primary, secondary) {
        // Archetypes → Layer 1
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

        // Themes → Layer 2
        edges.push(createEdge('themes', 'layer_color', COLORS.pink, { arrows: true }));

        // Date Seed → Layer 3
        edges.push(createEdge('date_seed', 'layer_variety', COLORS.orange, { arrows: true }));

        // All Layers → Final Prompt
        edges.push(createEdge('layer_structure', 'final_prompt', COLORS.purple, { arrows: true }));
        edges.push(createEdge('layer_color', 'final_prompt', COLORS.pink, { arrows: true }));
        edges.push(createEdge('layer_variety', 'final_prompt', COLORS.orange, { arrows: true }));
    }

    /**
     * Build the complete graph from derivation data.
     * 
     * @param {Object} data - Derivation data from API
     */
    function buildGraph(data) {
        const container = document.getElementById('graph-full-flow');
        if (!container) {
            console.warn('[Derivation] Graph container not found');
            return;
        }

        const nodes = [];
        const edges = [];

        // Extract data
        const news = data.news || {};
        const summary = data.summary || '';
        const metrics = data.input_metrics || {};
        const selection = data.selection || {};
        const allScores = selection.all_scores || [];
        const prompt = data.prompt || {};
        const components = prompt.components || {};
        const themes = data.themes || [];
        const dateSeed = data.date || new Date().toISOString().split('T')[0];
        const primary = selection.primary;
        const secondary = selection.secondary;
        const instrumentVariant = components.instrument_variant ?? 0;

        // Build nodes
        buildNewsNode(nodes, edges, news);
        buildStructuredOutputNode(nodes, edges, metrics, themes, summary);
        buildMetricNodes(nodes, edges, metrics);
        buildArchetypeNodes(nodes, edges, allScores, primary, secondary);
        buildThemesNode(nodes, edges, themes);
        buildDateSeedNode(nodes, edges, dateSeed, instrumentVariant);
        buildLayerNodes(nodes, edges, components);
        buildFinalPromptNode(nodes, edges, prompt);
        buildLayerEdges(edges, primary, secondary);

        // Create network
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

        // Enable keyboard navigation
        container.tabIndex = 0;

        // Fit view after initial render
        network.once('afterDrawing', function() {
            network.fit({
                animation: { duration: 300, easingFunction: 'easeInOutQuad' },
            });
        });

        console.log(`[Derivation] Built graph with ${nodes.length} nodes and ${edges.length} edges`);
    }

    // =========================================================================
    // Layout Reset
    // =========================================================================

    /**
     * Reset all nodes to their initial positions.
     */
    function resetLayout() {
        if (!network) return;

        const updates = Object.entries(initialPositions).map(([id, pos]) => ({
            id,
            x: pos.x,
            y: pos.y,
        }));

        network.body.data.nodes.update(updates);

        // Fit view after reset
        setTimeout(function() {
            network.fit({
                animation: { duration: 300, easingFunction: 'easeInOutQuad' },
            });
        }, 100);

        console.log('[Derivation] Layout reset');
    }

    // =========================================================================
    // Data Loading
    // =========================================================================

    /**
     * Fetch derivation data and build the graph.
     */
    async function loadAndBuildGraph() {
        try {
            console.log('[Derivation] Fetching data...');
            
            const response = await fetch(DERIVATION_API);
            
            if (!response.ok) {
                throw new Error(`API returned ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                console.error('[Derivation] API error:', data.error);
                showError(data.error);
                return;
            }

            buildGraph(data);

        } catch (error) {
            console.error('[Derivation] Failed to load data:', error);
            showError(error.message);
        }
    }

    /**
     * Show error message in the graph container.
     * 
     * @param {string} message - Error message to display
     */
    function showError(message) {
        const container = document.getElementById('graph-full-flow');
        if (container) {
            container.innerHTML = `
                <div style="color: ${COLORS.red}; padding: 20px; text-align: center;">
                    <p>Failed to load pipeline data</p>
                    <p style="color: ${COLORS.textDim}; font-size: 0.9em;">${message}</p>
                </div>
            `;
        }
    }

    // =========================================================================
    // Initialization
    // =========================================================================

    /**
     * Initialize the derivation visualization.
     */
    function init() {
        console.log('[Derivation] Initializing...');

        // Setup reset button
        const resetBtn = document.getElementById('reset-layout-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', resetLayout);
        }

        // Load and build graph
        loadAndBuildGraph();

        console.log('[Derivation] Initialization complete');
    }

    // =========================================================================
    // Entry Point
    // =========================================================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
