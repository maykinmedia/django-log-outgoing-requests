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
    var xmlDoc = new DOMParser().parseFromString(sourceXml, 'application/xml');
    var xsltDoc = new DOMParser().parseFromString([
        '<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform">',
        '  <xsl:strip-space elements="*"/>',
        '  <xsl:template match="node()|@*">',
        '    <xsl:copy>',
        '      <xsl:apply-templates select="node()|@*"/>',
        '    </xsl:copy>',
        '  </xsl:template>',
        '  <xsl:output method="xml" indent="yes"/>',
        '</xsl:stylesheet>',
    ].join('\n'), 'application/xml');

    var xsltProcessor = new XSLTProcessor();    
    xsltProcessor.importStylesheet(xsltDoc);
    var resultDoc = xsltProcessor.transformToDocument(xmlDoc);
    var resultXml = new XMLSerializer().serializeToString(resultDoc);
    return resultXml;
};

