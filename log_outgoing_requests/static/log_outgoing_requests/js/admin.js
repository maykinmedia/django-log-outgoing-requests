document.addEventListener("DOMContentLoaded", function () {
    const link = document.querySelector(".prettify-toggle-link");
    if (link) {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            const textArea = document.querySelector(".prettify-output");
            const contentType = textArea.getAttribute("content-type");
            const responseBody = textArea.value;
            if (textArea.style.display === "none") {
                let outputValue = '';
                if (contentType.includes('json')) {
                    try {
                        outputValue = JSON.stringify(JSON.parse(responseBody), null, 3);
                    } catch (error) {
                        outputValue = "Invalid JSON format";
                    }
                } else if (contentType.includes('xml')) {
                    try {
                        outputValue = prettifyXml(responseBody);
                    } catch (xmlError) {
                        outputValue = "Invalid XML format";
                    }
                }
                textArea.value = outputValue;
                textArea.style.display = "inline";
            } else {
                textArea.style.display = "none";
            }
        });
    }
});

var prettifyXml = function(sourceXml) {
    // Unfortunately, Firefox and Safari do not respect `indent="yes"`
    // when using `XSLTProcessor`, so we manually format the XML instead
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(sourceXml, "application/xml");

    function formatNode(node, indent = 0) {
        const PADDING = "  ";
        const indentStr = PADDING.repeat(indent);
        let xml = "";

        switch (node.nodeType) {
        case Node.ELEMENT_NODE:
            {
            // Collect all child nodes
            const children = Array.from(node.childNodes).filter(
                (n) => n.nodeType !== Node.COMMENT_NODE || n.nodeValue.trim() !== ""
            );

            // Open tag with attributes
            let openTag = `<${node.nodeName}`;
            for (let attr of node.attributes) {
                openTag += ` ${attr.name}="${attr.value}"`;
            }
            openTag += ">";

            // Determine if all children are text nodes
            const allText = children.every((n) => n.nodeType === Node.TEXT_NODE);

            if (children.length === 0) {
                // Empty element
                xml += indentStr + `<${node.nodeName}${[...node.attributes].map(a=>` ${a.name}="${a.value}"`).join('')}/>`;
            } else if (allText) {
                // Inline text
                const textContent = children.map((c) => c.nodeValue.trim()).join("");
                xml += indentStr + openTag + textContent + `</${node.nodeName}>`;
            } else {
                // Element with nested children
                xml += indentStr + openTag + "\n";
                for (let child of children) {
                const childXml = formatNode(child, indent + 1);
                if (childXml) xml += childXml + "\n";
                }
                xml += indentStr + `</${node.nodeName}>`;
            }
            }
            break;

        case Node.TEXT_NODE:
            {
            const text = node.nodeValue.trim();
            if (text) xml += indentStr + text;
            }
            break;

        case Node.CDATA_SECTION_NODE:
            xml += indentStr + `<![CDATA[${node.nodeValue}]]>`;
            break;

        case Node.COMMENT_NODE:
            xml += indentStr + `<!--${node.nodeValue.trim()}-->`;
            break;

        case Node.DOCUMENT_NODE:
            for (let child of node.childNodes) {
            xml += formatNode(child, indent) + "\n";
            }
            break;

        default:
            // Ignore other node types
            break;
        }

        return xml.trimEnd();
    }

    return formatNode(xmlDoc);
};
