(function () {
    const dataElement = document.getElementById("transit-dashboard-data");
    if (!dataElement) {
        return;
    }

    const chartData = JSON.parse(dataElement.textContent);
    const palette = ["#174a7c", "#2b7bbb", "#1d6f42", "#d68a13", "#7c3aed", "#0f766e", "#be123c", "#475569"];
    const tooltip = document.createElement("div");
    tooltip.className = "chart-tooltip";
    document.body.appendChild(tooltip);

    function setupCheckboxDropdowns() {
        const dropdowns = Array.from(document.querySelectorAll("[data-checkbox-dropdown]"));
        dropdowns.forEach((dropdown) => {
            const toggle = dropdown.querySelector(".checkbox-dropdown-toggle");
            const label = dropdown.querySelector("[data-checkbox-dropdown-label]");
            const checkboxes = Array.from(dropdown.querySelectorAll('input[type="checkbox"]'));

            function updateLabel() {
                const selected = checkboxes
                    .filter((checkbox) => checkbox.checked)
                    .map((checkbox) => checkbox.value);
                label.textContent = selected.length ? selected.join(", ") : "Seçilməyib";
            }

            toggle.addEventListener("click", () => {
                dropdowns.forEach((item) => {
                    if (item !== dropdown) {
                        item.classList.remove("open");
                    }
                });
                dropdown.classList.toggle("open");
            });
            checkboxes.forEach((checkbox) => checkbox.addEventListener("change", updateLabel));
            updateLabel();
        });

        document.addEventListener("click", (event) => {
            dropdowns.forEach((dropdown) => {
                if (!dropdown.contains(event.target)) {
                    dropdown.classList.remove("open");
                }
            });
        });
    }

    function formatValue(value) {
        return `${Math.round(value || 0).toLocaleString("en-US").replace(/,/g, " ")} ton`;
    }

    function showTooltip(event, title, value) {
        tooltip.innerHTML = `<strong>${title}</strong><span>${formatValue(value)}</span>`;
        tooltip.style.left = `${event.clientX + 14}px`;
        tooltip.style.top = `${event.clientY + 14}px`;
        tooltip.classList.add("visible");
    }

    function hideTooltip() {
        tooltip.classList.remove("visible");
    }

    function emptyState(container) {
        container.innerHTML = '<div class="chart-empty">Məlumat yoxdur</div>';
    }

    function svgEl(tag, attrs = {}) {
        const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
        Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
        return element;
    }

    function wrapLabel(label, maxChars) {
        const words = String(label || "").split(/\s+/).filter(Boolean);
        const lines = [];
        let current = "";

        words.forEach((word) => {
            if (word.length > maxChars) {
                if (current) {
                    lines.push(current);
                    current = "";
                }
                for (let index = 0; index < word.length; index += maxChars) {
                    lines.push(word.slice(index, index + maxChars));
                }
                return;
            }
            const candidate = current ? `${current} ${word}` : word;
            if (candidate.length > maxChars && current) {
                lines.push(current);
                current = word;
            } else {
                current = candidate;
            }
        });

        if (current) {
            lines.push(current);
        }
        return lines.length ? lines : [""];
    }

    function drawBar(container, data) {
        const labels = data.labels || [];
        const values = data.values || [];
        if (!labels.length) {
            emptyState(container);
            return;
        }

        const width = Math.max(container.clientWidth, 320);
        const labelWidth = Math.min(width * 0.48, Math.max(220, width * 0.36));
        const maxChars = Math.max(22, Math.floor(labelWidth / 7));
        const wrappedLabels = labels.map((label) => wrapLabel(label, maxChars));
        const rowHeights = wrappedLabels.map((lines) => Math.max(44, lines.length * 15 + 18));
        const height = Math.max(260, rowHeights.reduce((sum, rowHeight) => sum + rowHeight, 0) + 34);
        const barWidth = width - labelWidth - 60;
        const maxValue = Math.max(...values, 1);
        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, role: "img" });
        let y = 20;

        labels.forEach((label, index) => {
            const rowHeight = rowHeights[index];
            const labelLines = wrappedLabels[index];
            const barY = y + Math.max(8, (rowHeight - 18) / 2);
            const value = values[index] || 0;
            const length = Math.max(3, (value / maxValue) * barWidth);
            const color = palette[index % palette.length];

            const text = svgEl("text", {
                x: 0,
                y: y + 14,
                class: "chart-label",
            });
            labelLines.forEach((line, lineIndex) => {
                const tspan = svgEl("tspan", {
                    x: 0,
                    dy: lineIndex ? 15 : 0,
                });
                tspan.textContent = line;
                text.appendChild(tspan);
            });
            svg.appendChild(text);

            const track = svgEl("rect", {
                x: labelWidth,
                y: barY,
                width: barWidth,
                height: 18,
                rx: 9,
                class: "chart-track",
            });
            svg.appendChild(track);

            const bar = svgEl("rect", {
                x: labelWidth,
                y: barY,
                width: length,
                height: 18,
                rx: 9,
                fill: color,
                class: "chart-bar",
            });
            bar.addEventListener("mousemove", (event) => showTooltip(event, label, value));
            bar.addEventListener("mouseleave", hideTooltip);
            svg.appendChild(bar);

            svg.appendChild(svgEl("text", {
                x: labelWidth + Math.min(length + 8, barWidth - 76),
                y: barY + 15,
                class: "chart-value",
            })).textContent = formatValue(value);
            y += rowHeight;
        });

        container.innerHTML = "";
        container.appendChild(svg);
    }

    function drawLine(container, data) {
        const labels = data.labels || [];
        const values = data.values || [];
        if (!labels.length) {
            emptyState(container);
            return;
        }

        const width = Math.max(container.clientWidth, 360);
        const height = 310;
        const padding = { top: 24, right: 24, bottom: 44, left: 60 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;
        const maxValue = Math.max(...values, 1);
        const points = values.map((value, index) => {
            const x = padding.left + (labels.length === 1 ? chartWidth / 2 : (index / (labels.length - 1)) * chartWidth);
            const y = padding.top + chartHeight - (value / maxValue) * chartHeight;
            return [x, y, value, labels[index]];
        });

        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, role: "img" });
        [0, 0.25, 0.5, 0.75, 1].forEach((tick) => {
            const y = padding.top + chartHeight - tick * chartHeight;
            svg.appendChild(svgEl("line", {
                x1: padding.left,
                x2: width - padding.right,
                y1: y,
                y2: y,
                class: "chart-grid-line",
            }));
        });

        const path = points.map((point, index) => `${index ? "L" : "M"} ${point[0]} ${point[1]}`).join(" ");
        svg.appendChild(svgEl("path", {
            d: path,
            class: "chart-line-path",
        }));

        points.forEach(([x, y, value, label]) => {
            const point = svgEl("circle", {
                cx: x,
                cy: y,
                r: 5,
                class: "chart-point",
            });
            point.addEventListener("mousemove", (event) => showTooltip(event, label, value));
            point.addEventListener("mouseleave", hideTooltip);
            svg.appendChild(point);
            svg.appendChild(svgEl("text", {
                x,
                y: height - 14,
                class: "chart-axis-label",
                "text-anchor": "middle",
            })).textContent = label;
        });

        container.innerHTML = "";
        container.appendChild(svg);
    }

    function polarToCartesian(cx, cy, radius, angle) {
        const radians = (angle - 90) * Math.PI / 180;
        return {
            x: cx + radius * Math.cos(radians),
            y: cy + radius * Math.sin(radians),
        };
    }

    function describeArc(cx, cy, radius, startAngle, endAngle) {
        const start = polarToCartesian(cx, cy, radius, endAngle);
        const end = polarToCartesian(cx, cy, radius, startAngle);
        const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
        return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
    }

    function drawDonut(container, data) {
        const labels = data.labels || [];
        const values = data.values || [];
        const total = values.reduce((sum, value) => sum + value, 0);
        if (!labels.length || !total) {
            emptyState(container);
            return;
        }

        const width = Math.max(container.clientWidth, 320);
        const height = 310;
        const cx = 126;
        const cy = 146;
        const radius = 86;
        let angle = 0;
        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, role: "img" });

        values.forEach((value, index) => {
            const sliceAngle = (value / total) * 360;
            const path = svgEl("path", {
                d: describeArc(cx, cy, radius, angle, angle + sliceAngle),
                stroke: palette[index % palette.length],
                "stroke-width": 34,
                fill: "none",
                class: "donut-slice",
            });
            path.addEventListener("mousemove", (event) => showTooltip(event, labels[index], value));
            path.addEventListener("mouseleave", hideTooltip);
            svg.appendChild(path);
            angle += sliceAngle;
        });

        svg.appendChild(svgEl("text", {
            x: cx,
            y: cy - 4,
            class: "donut-total",
            "text-anchor": "middle",
        })).textContent = formatValue(total);
        svg.appendChild(svgEl("text", {
            x: cx,
            y: cy + 20,
            class: "donut-caption",
            "text-anchor": "middle",
        })).textContent = "cəmi";

        labels.forEach((label, index) => {
            const x = 245;
            const y = 54 + index * 28;
            svg.appendChild(svgEl("rect", {
                x,
                y: y - 11,
                width: 12,
                height: 12,
                rx: 3,
                fill: palette[index % palette.length],
            }));
            svg.appendChild(svgEl("text", {
                x: x + 18,
                y,
                class: "chart-label",
            })).textContent = label.length > 32 ? `${label.slice(0, 32)}...` : label;
        });

        container.innerHTML = "";
        container.appendChild(svg);
    }

    function drawFlow(container, data) {
        const labels = data.labels || [];
        const values = data.values || [];
        if (!labels.length) {
            emptyState(container);
            return;
        }

        const width = Math.max(container.clientWidth, 420);
        const rowHeight = 44;
        const height = labels.length * rowHeight + 36;
        const maxValue = Math.max(...values, 1);
        const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, role: "img" });

        labels.forEach((label, index) => {
            const y = 22 + index * rowHeight;
            const value = values[index] || 0;
            const strokeWidth = Math.max(4, (value / maxValue) * 18);
            const color = palette[index % palette.length];
            const line = svgEl("path", {
                d: `M 18 ${y} C ${width * 0.34} ${y - 18}, ${width * 0.58} ${y + 18}, ${width - 18} ${y}`,
                stroke: color,
                "stroke-width": strokeWidth,
                fill: "none",
                "stroke-linecap": "round",
                class: "flow-line",
            });
            line.addEventListener("mousemove", (event) => showTooltip(event, label, value));
            line.addEventListener("mouseleave", hideTooltip);
            svg.appendChild(line);
            svg.appendChild(svgEl("text", {
                x: 20,
                y: y + 22,
                class: "chart-label",
            })).textContent = label.length > 72 ? `${label.slice(0, 72)}...` : label;
            svg.appendChild(svgEl("text", {
                x: width - 20,
                y: y + 22,
                class: "chart-value",
                "text-anchor": "end",
            })).textContent = formatValue(value);
        });

        container.innerHTML = "";
        container.appendChild(svg);
    }

    function renderChart(container) {
        const key = container.dataset.chartKey;
        const data = chartData[key];
        if (!data) {
            emptyState(container);
            return;
        }
        if (data.type === "line") {
            drawLine(container, data);
        } else if (data.type === "donut") {
            drawDonut(container, data);
        } else if (data.type === "flow") {
            drawFlow(container, data);
        } else {
            drawBar(container, data);
        }
    }

    function renderAll() {
        document.querySelectorAll(".svg-chart").forEach(renderChart);
    }

    window.addEventListener("resize", () => {
        window.clearTimeout(window.transitDashboardResizeTimer);
        window.transitDashboardResizeTimer = window.setTimeout(renderAll, 120);
    });
    setupCheckboxDropdowns();
    renderAll();
})();
