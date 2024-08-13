const gameArea = document.getElementById("gameArea");
const persistantGameArea = document.getElementById("persistentGameArea");

const CrystalButton = document.getElementById("crystalButton");
const DungeonButton = document.getElementById("dungeonButton");
const InventoryButton = document.getElementById("inventoryButton");
const SkillsButton = document.getElementById("skillsButton");
const FarmButton = document.getElementById("farmButton");
const CraftingButton = document.getElementById("craftingButton");
const TradingButton = document.getElementById("tradingButton");
const BlacksmithButton = document.getElementById("blacksmithButton");

CrystalButton.addEventListener("click", () => {
    gameArea.src = "/pages/crystalGameArea.html";
})

document.addEventListener('DOMContentLoaded', function () {
    const iframe = gameArea;

    if (iframe) {
        iframe.onload = function () {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

            const styles = `
                :root {
                    --textColor: ${getComputedStyle(document.documentElement).getPropertyValue('--textColor')};
                    --col1: ${getComputedStyle(document.documentElement).getPropertyValue('--col1')};
                    --col2: ${getComputedStyle(document.documentElement).getPropertyValue('--col2')};
                    --col3: ${getComputedStyle(document.documentElement).getPropertyValue('--col3')};
                    --col4: ${getComputedStyle(document.documentElement).getPropertyValue('--col4')};
                }
            `;

            const styleElement = iframeDoc.createElement('style');
            styleElement.textContent = styles;
            iframeDoc.head.appendChild(styleElement);
        };
    } else {
        console.error('Iframe element not found');
    }
});