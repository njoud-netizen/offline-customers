"""زر "نسخ الصفوف" بصفحة اوت باوند: ينسخ النص للحافظة من المتصفح مباشرة، بدون أي اتصال بالشيت.
الملف منفصل ويُستورد وقت الحاجة فقط، حتى ما يأثر إصدار Streamlit القديم على باقي الصفحات."""
from streamlit.components.v2 import component

_HTML = '<div class="copy-box"><button type="button"></button><div class="message" role="status"></div></div>'

_CSS = """
.copy-box { font-family: var(--st-font); }
button {
    width: 100%;
    min-height: 3rem;
    padding: 0.4rem 0.75rem;
    border: 1px solid var(--st-primary-color);
    border-radius: 12px;
    background: var(--st-primary-color);
    color: #fff;
    font: inherit;
    cursor: pointer;
}
button:hover { opacity: 0.9; }
button:focus-visible { outline: 2px solid var(--st-primary-color); outline-offset: 2px; }
.message { margin-top: 0.4rem; font-size: 0.9rem; text-align: center; }
.message:empty { display: none; }
.message.ok { color: var(--st-green-text-color, #1f7a4d); }
.message.failed { color: var(--st-red-text-color, #b3261e); }
"""

_JS = """
async function writeToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
    }
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    const copied = document.execCommand("copy");
    area.remove();
    if (!copied) throw new Error("copy failed");
}

export default function (component) {
    const { data, parentElement } = component;
    const box = parentElement.querySelector(".copy-box");
    const button = parentElement.querySelector("button");
    const message = parentElement.querySelector(".message");

    box.dir = data.direction;
    button.textContent = data.label;
    if (button.copyText !== data.text) {
        message.textContent = "";
        message.className = "message";
    }
    button.copyText = data.text;
    button.onclick = async () => {
        try {
            await writeToClipboard(button.copyText);
            message.textContent = data.copied_message;
            message.className = "message ok";
        } catch (e) {
            message.textContent = data.failed_message;
            message.className = "message failed";
        }
    };
}
"""

_copy_button = component("outbound_copy_rows", html=_HTML, css=_CSS, js=_JS)


def render_copy_button(text: str, label: str, copied_message: str, failed_message: str, direction: str) -> None:
    _copy_button(
        data={
            "text": text,
            "label": label,
            "copied_message": copied_message,
            "failed_message": failed_message,
            "direction": direction,
        },
        key="outbound_copy_rows",
    )
