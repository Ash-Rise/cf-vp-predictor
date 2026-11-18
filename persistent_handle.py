"""A browser-persistent Streamlit handle input using built-in Components v2.

The handle is stored only in the current browser's localStorage. No extra
server-side database, cookie service, or third-party component is required.
Requires Streamlit >= 1.51.
"""

import streamlit as st


_HANDLE_HTML = '<label for="cf-handle-input"></label><input id="cf-handle-input" type="text" autocomplete="off" spellcheck="false" />'
_HANDLE_CSS = """
label {
  display: block;
  font-family: var(--st-font);
  color: var(--st-text-color);
  font-size: 0.875rem;
  margin-bottom: 0.45rem;
}
input {
  box-sizing: border-box;
  width: 100%;
  padding: 0.55rem 0.75rem;
  color: var(--st-text-color);
  background: var(--st-background-color);
  border: 1px solid var(--st-border-color, #999);
  border-radius: 0.5rem;
  font-family: var(--st-font);
  font-size: 1rem;
}
input:focus { outline: 2px solid var(--st-primary-color); outline-offset: 1px; }
"""
_HANDLE_JS = """
export default function({parentElement, data, setStateValue}) {
  const label = parentElement.querySelector('label');
  const input = parentElement.querySelector('input');
  label.textContent = data.label;
  const storageKey = 'cf-vp-predictor:last-handle';

  // Only the first mount reads localStorage. Later reruns use Python state.
  if (!parentElement.dataset.initialized) {
    parentElement.dataset.initialized = '1';
    let saved = null;
    try { saved = window.localStorage.getItem(storageKey); } catch (_) {}
    const initial = saved && saved.trim() ? saved.trim() : (data.value || '');
    input.value = initial;
    if (initial !== data.value) setStateValue('value', initial);
  } else if (input !== document.activeElement && input.value !== data.value) {
    input.value = data.value || '';
  }

  input.oninput = () => {
    try {
      const value = input.value.trim();
      if (value) window.localStorage.setItem(storageKey, value);
      else window.localStorage.removeItem(storageKey);
    } catch (_) { /* private browsing or blocked storage */ }
  };
  const commit = () => {
    const value = input.value.trim();
    if (value !== data.value) setStateValue('value', value);
  };
  input.onchange = commit;
  input.onblur = commit;
  input.onkeydown = (event) => {
    if (event.key === 'Enter') { event.preventDefault(); commit(); input.blur(); }
  };
}
"""

_handle_component = st.components.v2.component(
    "cf_vp_persistent_handle",
    html=_HANDLE_HTML,
    css=_HANDLE_CSS,
    js=_HANDLE_JS,
)


def persistent_handle_input(label, *, default=""):
    """Render the input in the active container and return its committed value."""
    key = "cf_persistent_handle"
    state = st.session_state.get(key, {})
    value = state.get("value", default)
    result = _handle_component(
        data={"label": label, "value": value},
        default={"value": value},
        key=key,
        on_value_change=lambda: None,
    )
    return (result.value or "").strip()
