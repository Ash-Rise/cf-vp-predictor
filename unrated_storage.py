"""Keep per-VP Unrated selections in this browser (not on the server).

Components v2 sends a saved list to Python when its localStorage data is read.
A write is performed only when the user actually changes the table. No
submission history, password, or API response is stored in the browser.
"""
import json

import streamlit as st

_COMPONENT_JS = r"""
export default function({parentElement, data, setStateValue}) {
  const handle = (data.handle || '').trim().toLowerCase();
  const key = 'cf-vp-predictor:unrated:' + handle;
  const state = data.write;
  // Read once on mount and again if the user switches Handle.
  if (parentElement.dataset.handle !== handle) {
    parentElement.dataset.handle = handle;
    let raw = '[]';
    try { raw = window.localStorage.getItem(key) || '[]'; } catch (_) {}
    try {
      const ids = JSON.parse(raw);
      setStateValue('read', JSON.stringify({handle, keys: Array.isArray(ids) ? ids : []}));
    } catch (_) {
      setStateValue('read', JSON.stringify({handle, keys: []}));
    }
  }
  // Only explicit checkbox edits may trigger writes. Do not overwrite storage
  // during initial loading, reruns or a Handle switch.
  if (state && state.handle === handle && state.nonce &&
      parentElement.dataset.lastWrite !== state.nonce) {
    parentElement.dataset.lastWrite = state.nonce;
    try {
      window.localStorage.setItem(key, JSON.stringify(state.keys));
    } catch (_) {}
  }
}
"""
# Component source is JS, rendered as a tiny transparent area.
_COMPONENT = st.components.v2.component(
    "cf_vp_unrated_storage",
    html="<span style='display:none' aria-hidden='true'></span>",
    js=_COMPONENT_JS,
)


def parse_saved_value(raw, expected_handle, valid_keys):
    """Never apply another Handle's settings or stale sessions."""
    try:
        payload = json.loads(raw or "")
        if payload.get("handle") != expected_handle.casefold():
            return None
        keys = payload.get("keys")
        if not isinstance(keys, list):
            return None
        return {k for k in keys if isinstance(k, str) and k in valid_keys}
    except (ValueError, AttributeError, TypeError):
        return None


def sync_unrated_storage(handle, selected, *, write=None):
    """Return a freshly read set, if available, else None.

    The optional write is {handle, keys, nonce}; caller must supply it only
    after a user-initiated table edit. Existing Python session settings remain
    authoritative until a valid browser response arrives.
    """
    result = _COMPONENT(
        data={"handle": handle, "write": write},
        default={"read": ""},
        key="unrated_browser_storage",
        on_read_change=lambda: None,
    )
    return result.read or ""
