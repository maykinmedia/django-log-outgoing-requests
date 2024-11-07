const getCsrfTokenFromDom = () => {
    return document.querySelector("[name=csrfmiddlewaretoken]").value;
};

document.addEventListener("DOMContentLoaded", function () {
    const prettifyAnchors = document.querySelectorAll(
        ".prettify-body-response"
    );
    const originalAnchors = document.querySelectorAll(
        ".original-body-response"
    );
    const url = window.location.href;

    prettifyAnchors.forEach(function (element) {
        const responseBodyText = document.querySelector(".body-response-text");

        element.addEventListener("click", function (event) {
            event.preventDefault();

            fetch(element.href, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": getCsrfTokenFromDom(),
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ url: url, text: element.textContent }),
            })
                .then((response) => response.json())
                .then((data) => {
                    responseBodyText.textContent = data.newValue;
                })
                .catch((error) => {
                    console.error("Error:", error);
                });
        });
    });

    originalAnchors.forEach(function (element) {
        const responseBodyText = document.querySelector(".body-response-text");

        element.addEventListener("click", function (event) {
            event.preventDefault();

            fetch(element.href, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": getCsrfTokenFromDom(),
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ url: url, text: element.textContent }),
            })
                .then((response) => response.json())
                .then((data) => {
                    responseBodyText.textContent = data.newValue;
                })
                .catch((error) => {
                    console.error("Error:", error);
                });
        });
    });
});
