// Set up dimensions and color scale
const width = window.innerWidth;
const height = window.innerHeight;
const color = d3.scaleOrdinal(d3.schemeCategory10);

// Create SVG container
const svg = d3.select("#graph")
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .style("background-color", "#1a1a1a")
    .call(d3.zoom().on("zoom", (event) => {
        svg.attr("transform", event.transform);
    }))
    .append("g");

// Tooltip setup
const tooltip = d3.select("#tooltip");

// Initialize selectors and global variables
const bookSelect = document.getElementById('bookSelect');
const iterSelect = document.getElementById('iterSelect');
let currentBookData = null;
let nodes = [], links = []; // Global variables for tooltip access

// Load JSON file list and populate selectors
d3.json('jsons.json').then(books => {
    // Populate book selector
    const bookNames = Object.keys(books);
    bookNames.sort(); // Sort book names alphabetically

    bookNames.forEach(bookName => {
        const [prefix, maxIter] = books[bookName];
        const option = document.createElement('option');
        option.value = JSON.stringify([bookName, prefix, maxIter]);
        option.text = bookName;
        bookSelect.appendChild(option);
    });

    // Find Tom Sawyer and select it by default
    const tomSawyerOption = Array.from(bookSelect.options).find(option =>
        option.text.includes("TOM SAWYER"));
    if (tomSawyerOption) {
        tomSawyerOption.selected = true;
    }

    // Trigger initial load
    bookSelect.dispatchEvent(new Event('change'));
}).catch(error => {
    console.error("Error loading the file list:", error);
});

// Handle book selection change
bookSelect.addEventListener('change', () => {
    currentBookData = JSON.parse(bookSelect.value);
    const [bookName, prefix, maxIter] = currentBookData;

    // Update iteration selector
    iterSelect.innerHTML = '';

    // Load all iteration data to get counts
    Promise.all(Array.from({ length: maxIter }, (_, i) =>
        d3.json(`data/${prefix}_${i}.json`)
    )).then(allData => {
        for (let i = 0; i < maxIter; i++) {
            const data = allData[i];
            const option = document.createElement('option');
            option.value = i;
            option.text = `Iteration ${i + 1} (${data.characters.length} characters, ${data.relations.length} relations)`;
            iterSelect.appendChild(option);
        }

        // Select last iteration by default
        iterSelect.value = maxIter - 1;

        // Load the visualization
        loadData();
    });
});

// Handle iteration selection change
iterSelect.addEventListener('change', loadData);

// Function to load data based on current selections
function loadData() {
    if (!currentBookData) return;

    const [bookName, prefix, maxIter] = currentBookData;
    const iteration = iterSelect.value;
    const fileName = `data/${prefix}_${iteration}.json`;

    d3.json(fileName).then(data => {
        nodes = data.characters;
        links = data.relations;
        createVisualization(data);
    }).catch(error => {
        console.error("Error loading the data:", error);
    });
}

// Function to create visualization
function createVisualization(data) {
    // Clear existing visualization
    svg.selectAll("*").remove();

    // Process data
    nodes = data.characters;
    links = data.relations.map(d => ({
        ...d,
        source: d.id1,
        target: d.id2
    }));

    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links)
            .id(d => d.id)
            .distance(d => 100 - d.weight * 5)
            .strength(0.7))
        .force("charge", d3.forceManyBody()
            .strength(-400)
            .distanceMax(350))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(d => d.main_character ? 20 : 15))
        .force("x", d3.forceX(width / 2).strength(0.05))
        .force("y", d3.forceY(height / 2).strength(0.05))
        .alphaDecay(0.02)
        .velocityDecay(0.4);

    // Create links
    const link = svg.append("g")
        .selectAll("line")
        .data(links)
        .enter().append("line")
        .attr("class", "link")
        .attr("stroke-width", d => Math.sqrt(d.weight))
        .style("stroke", d => {
            if (d.positivity < -0.2) return "#ff4444";
            if (d.positivity > 0.2) return "#44ff44";
            return "#888888";
        })
        .style("stroke-opacity", 0.6);

    // Create node groups
    const nodeGroup = svg.append("g")
        .selectAll("g")
        .data(nodes)
        .enter()
        .append("g")
        .attr("class", "node")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    // Add border circles for main characters
    nodeGroup.filter(d => d.main_character)
        .append("circle")
        .attr("r", 12)
        .attr("fill", "none")
        .attr("stroke", "#ffffff")
        .attr("stroke-width", 2);

    // Add images or circles for nodes
    const defs = svg.append("defs");

    nodeGroup.each(function (d) {
        const node = d3.select(this);
        const prefix = currentBookData[1];
        const imagePath = `data/${prefix}/${d.common_name}.png`;

        // Create a pattern for the image
        const pattern = defs.append("pattern")
            .attr("id", `img-${d.id}`)
            .attr("width", 1)
            .attr("height", 1)
            .attr("patternUnits", "objectBoundingBox");

        // Create the circle first (this will be the event target)
        const circle = node.append("circle")
            .attr("r", d.main_character ? 10 : 6)
            .attr("fill", color(d.id))
            .on("mouseover", showNodeTooltip)
            .on("mouseout", hideTooltip)
            .on("click", (event, d) => showNodeInfo(d));

        // Try to load the image
        const img = new Image();
        img.onload = function () {
            pattern.append("image")
                .attr("xlink:href", imagePath)
                .attr("width", d.main_character ? 20 : 12)
                .attr("height", d.main_character ? 20 : 12);

            circle.attr("fill", `url(#img-${d.id})`);
        };
        img.src = imagePath;
    });

    // Add labels
    const labels = svg.append("g")
        .selectAll("text")
        .data(nodes)
        .enter().append("text")
        .attr("class", "label")
        .text(d => d.common_name)
        .attr("font-size", d => d.main_character ? 14 : 12)
        .attr("dx", 15)
        .attr("dy", 4);

    // Update positions on each tick
    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        nodeGroup
            .attr("transform", d => `translate(${d.x},${d.y})`);

        labels
            .attr("x", d => d.x)
            .attr("y", d => d.y);
    });

    // Add link hover functionality
    link.on("mouseover", function (event, d) {
        const source = nodes.find(n => n.id === d.source.id);
        const target = nodes.find(n => n.id === d.target.id);
        tooltip.classed("hidden", false)
            .html(`
                <h3>Relationship</h3>
                <p><b>${source.common_name}</b> ↔ <b>${target.common_name}</b></p>
                <p>Type: ${d.relation.join(', ')}</p>
                <p>Strength: ${d.weight}</p>
                <p>Positivity: ${d.positivity > 0 ? '+' : ''}${d.positivity}</p>
            `)
            .style("left", `${event.pageX + 15}px`)
            .style("top", `${event.pageY - 28}px`);
    });

    link.on("mouseout", hideTooltip);

    // Drag functions
    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.2).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }

    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
        simulation.alpha(0.3);
        simulation.restart();
    }

    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0.05);
        event.subject.fx = event.x;
        event.subject.fy = event.y;
        setTimeout(() => {
            event.subject.fx = null;
            event.subject.fy = null;
        }, 1000);
    }
}

// Node info display function
function showNodeInfo(d) {
    const namesList = d.names.map(name => `${name}`).join(', ');
    const relations = links.filter(l => l.source.id === d.id || l.target.id === d.id)
        .map(l => {
            const other = l.source.id === d.id ? nodes.find(n => n.id === l.target.id) : nodes.find(n => n.id === l.source.id);
            const positivity = l.positivity > 0 ? `+${l.positivity}` : l.positivity;
            return `<div class="relation-item">
                <strong>${other.common_name}</strong><br>
                Type: ${l.relation.join(', ')}<br>
                Strength: ${l.weight}<br>
                Positivity: ${positivity}
            </div>`;
        }).join('');

    const infoContent = `
        ${d.description ? `<p>${d.description}</p>` : ''}
        ${d.portrait_prompt ? `
            <h3>Image Generation Prompt:</h3>
            <p class="image-prompt">${d.portrait_prompt}</p>
        ` : ''}
        <h3>Also known as:</h3>
        <p>${namesList}</p>
        <h3>Relationships:</h3>
        <div class="relations-list">
            ${relations}
        </div>
    `;

    // Try to load character image
    const prefix = currentBookData[1];
    const imagePath = `data/${prefix}/${d.common_name}.png`;

    if (window.innerHeight > window.innerWidth) { // Portrait orientation indicates mobile
        // Mobile view
        document.getElementById('mobile-char-name').innerHTML = d.common_name;
        document.getElementById('mobile-char-description').innerHTML = infoContent;
        const mobileImage = document.getElementById('mobile-char-image');

        // Check if image exists
        fetch(imagePath)
            .then(response => {
                if (response.ok) {
                    mobileImage.src = imagePath;
                    mobileImage.classList.remove('hidden');
                } else {
                    mobileImage.classList.add('hidden');
                }
            })
            .catch(() => mobileImage.classList.add('hidden'));

        document.getElementById('mobile-popup').classList.add('visible');
    } else {
        // Desktop view
        document.getElementById('char-name').innerHTML = d.common_name;
        document.getElementById('char-description').innerHTML = infoContent;
        const charImage = document.getElementById('char-image');

        // Check if image exists
        fetch(imagePath)
            .then(response => {
                if (response.ok) {
                    charImage.src = imagePath;
                    charImage.classList.remove('hidden');
                } else {
                    charImage.classList.add('hidden');
                }
            })
            .catch(() => charImage.classList.add('hidden'));

        document.getElementById('info-panel').classList.remove('hidden');
        document.getElementById('graph').style.width = '75%';
    }
}

// Node tooltip hover function
function showNodeTooltip(event, d) {
    tooltip.classed("hidden", false)
        .html(`
        <h3>${d.common_name}</h3>
        <p>${d.description || ''}</p>
        `)
        .style("left", `${event.pageX + 15}px`)
        .style("top", `${event.pageY - 28}px`);
}

// Tooltip hide function
function hideTooltip() {
    tooltip.classed("hidden", true);
}

// Initialize mobile popup close button
document.getElementById('close-popup').addEventListener('click', () => {
    document.getElementById('mobile-popup').classList.remove('visible');
});

// Handle window resize
window.addEventListener('resize', () => {
    const infoPanel = document.getElementById('info-panel');
    const graph = document.getElementById('graph');

    if (window.innerHeight > window.innerWidth) { // Portrait orientation indicates mobile
        infoPanel.classList.add('hidden');
        graph.style.width = '100%';
    } else if (!infoPanel.classList.contains('hidden')) {
        graph.style.width = '75%';
    }
});
