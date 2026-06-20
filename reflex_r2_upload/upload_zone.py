"""Upload zone UI + browser runtime script."""

from __future__ import annotations

import hashlib

import reflex as rx

from reflex_r2_upload.auth import issue_upload_token, upload_auth_enabled

UPLOAD_RUNTIME_SCRIPT = r"""
(() => {
  if (window.__reflexR2Upload) return;
  window.__reflexR2Upload = true;

  const BRIDGE_VERSION = 1;
  const ERROR_CODE = {
    R2_NOT_CONFIGURED: "R2_NOT_CONFIGURED",
    CONFIG_FETCH_FAILED: "CONFIG_FETCH_FAILED",
    UPLOAD_FAILED: "UPLOAD_FAILED",
    STORAGE_PUT_FAILED: "STORAGE_PUT_FAILED",
    CORS_BLOCKED: "CORS_BLOCKED",
    UNAUTHORIZED: "UNAUTHORIZED",
  };

  function bridgeError(message, code) {
    const body = { version: BRIDGE_VERSION, error: true, message };
    if (code) body.code = code;
    return body;
  }

  function classifyUploadError(message) {
    if (/R2 未配置|缺少：/i.test(message)) return ERROR_CODE.R2_NOT_CONFIGURED;
    if (/读取上传配置失败/i.test(message)) return ERROR_CODE.CONFIG_FETCH_FAILED;
    if (/未授权/i.test(message)) return ERROR_CODE.UNAUTHORIZED;
    if (/CORS|failed to fetch/i.test(message)) return ERROR_CODE.CORS_BLOCKED;
    if (/存储 PUT 失败/i.test(message)) return ERROR_CODE.STORAGE_PUT_FAILED;
    return ERROR_CODE.UPLOAD_FAILED;
  }

  function successPayload(zone, results) {
    const keyPrefix = zone.dataset.keyPrefix;
    if (results.length === 1) {
      const item = results[0];
      return {
        version: item.version || BRIDGE_VERSION,
        error: false,
        ok: true,
        keyPrefix: item.keyPrefix || keyPrefix,
        storagePath: item.storagePath,
        originalFilename: item.originalFilename,
        fileSizeBytes: item.fileSizeBytes,
        contentType: item.contentType,
        publicUrl: item.publicUrl ?? null,
        bridgeSignature: item.bridgeSignature,
      };
    }
    return {
      version: BRIDGE_VERSION,
      error: false,
      keyPrefix,
      files: results.map((item) => ({
        version: item.version || BRIDGE_VERSION,
        error: false,
        ok: true,
        keyPrefix: item.keyPrefix || keyPrefix,
        storagePath: item.storagePath,
        originalFilename: item.originalFilename,
        fileSizeBytes: item.fileSizeBytes,
        contentType: item.contentType,
        publicUrl: item.publicUrl ?? null,
        bridgeSignature: item.bridgeSignature,
      })),
    };
  }

  async function resolveBackendBase() {
    const root = document.querySelector("[data-backend-base]");
    const configured = root?.dataset?.backendBase;
    if (configured !== undefined && configured !== "") return configured;

    const host = window.location.hostname;
    const isLocal = ["localhost", "127.0.0.1", "0.0.0.0"].includes(host);
    if (!isLocal) return "";

    try {
      const res = await fetch("/env.json", { cache: "no-store" });
      if (res.ok) {
        const env = await res.json();
        if (env.PING) return new URL(env.PING).origin;
      }
    } catch (_error) {}

    return `http://${host}:8000`;
  }

  function routePrefix() {
    const root = document.querySelector("[data-route-prefix]");
    return (root?.dataset?.routePrefix || "/_reflex_r2_upload").replace(/\/$/, "");
  }

  async function internalFetch(path, options = {}) {
    const base = await resolveBackendBase();
    return fetch(`${base}${path}`, {
      credentials: "same-origin",
      ...options,
    });
  }

  function uploadTokenForZone(zone) {
    return zone.dataset.uploadToken || "";
  }

  async function readError(res) {
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") return data.detail;
      if (Array.isArray(data?.detail)) {
        return data.detail.map((x) => x.msg || String(x)).join("; ");
      }
    } catch (_error) {}
    return `${res.status} ${res.statusText}`;
  }

  function setStatus(zone, text, isError = false) {
    const el = zone.querySelector("[data-r2-status]");
    if (!el) return;
    el.textContent = text || "";
    el.dataset.r2StatusError = isError ? "1" : "0";
  }

  function notifyBridge(zone, payload) {
    const bridgeId = zone.dataset.bridgeId;
    if (!bridgeId) return;
    const input = document.getElementById(bridgeId);
    if (!input) return;
    const json = JSON.stringify(payload);
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      "value"
    )?.set;
    if (setter) setter.call(input, json);
    else input.value = json;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  async function fetchConfig() {
    const res = await internalFetch(`${routePrefix()}/config`, { cache: "no-store" });
    if (!res.ok) throw new Error(await readError(res));
    return res.json();
  }

  async function presign(zone, keyPrefix, filename, contentType, fileSizeBytes) {
    const res = await internalFetch(`${routePrefix()}/presign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        keyPrefix,
        filename,
        contentType,
        fileSizeBytes,
        uploadToken: uploadTokenForZone(zone),
      }),
    });
    if (!res.ok) throw new Error(await readError(res));
    return res.json();
  }

  async function putToStorage(uploadUrl, file, contentType) {
    const res = await fetch(uploadUrl, {
      method: "PUT",
      headers: { "Content-Type": contentType },
      body: file,
    });
    if (!res.ok) throw new Error(`存储 PUT 失败 (${res.status})`);
  }

  async function complete(zone, keyPrefix, payload) {
    const res = await internalFetch(`${routePrefix()}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        keyPrefix,
        uploadToken: uploadTokenForZone(zone),
        ...payload,
      }),
    });
    if (!res.ok) throw new Error(await readError(res));
    return res.json();
  }

  async function uploadOne(zone, file) {
    const keyPrefix = zone.dataset.keyPrefix;
    const contentType = zone.dataset.contentType || "application/octet-stream";

    const presignData = await presign(
      zone,
      keyPrefix,
      file.name,
      contentType,
      file.size
    );
    await putToStorage(
      presignData.uploadUrl,
      file,
      presignData.contentType || contentType
    );
    return complete(zone, keyPrefix, {
      storagePath: presignData.storagePath,
      originalFilename: file.name,
      fileSizeBytes: file.size,
    });
  }

  async function handleZoneFiles(zone, fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    setStatus(zone, "准备上传...");
    try {
      const cfg = await fetchConfig();
      if (!cfg.ready) {
        throw new Error("R2 未配置，请设置 .env 中的 R2_* 环境变量");
      }
    } catch (error) {
      const msg = error.message || "读取上传配置失败";
      setStatus(zone, msg, true);
      notifyBridge(
        zone,
        bridgeError(msg, classifyUploadError(msg))
      );
      return;
    }

    const results = [];
    const errors = [];

    for (let i = 0; i < files.length; i += 1) {
      const file = files[i];
      const prefix = files.length > 1 ? `(${i + 1}/${files.length}) ` : "";
      setStatus(zone, `${prefix}正在上传 ${file.name}...`);
      try {
        results.push(await uploadOne(zone, file));
      } catch (error) {
        let msg = error.message || String(error);
        if (/failed to fetch/i.test(msg)) {
          msg += "（可能是 Cloudflare R2 桶未配置 CORS，需允许本站 PUT）";
        }
        errors.push(`${file.name}: ${msg}`);
      }
    }

    if (results.length && !errors.length) {
      const payload = successPayload(zone, results);
      const msg =
        results.length === 1
          ? `已上传：${results[0].originalFilename}`
          : `已上传 ${results.length} 个文件`;
      setStatus(zone, msg);
      notifyBridge(zone, payload);
      return;
    }

    const msg = errors[0] || "上传失败";
    setStatus(zone, msg, true);
    notifyBridge(zone, bridgeError(msg, classifyUploadError(msg)));
  }

  function onZoneChange(event) {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) || input.type !== "file") return;
    const zone = input.closest("[data-r2-upload-zone]");
    if (!zone) return;
    void handleZoneFiles(zone, input.files);
    input.value = "";
  }

  function onZoneDragOver(event) {
    const zone = event.target.closest("[data-r2-upload-zone]");
    if (!zone || zone.dataset.noDrag === "1") return;
    event.preventDefault();
  }

  function onZoneDrop(event) {
    const zone = event.target.closest("[data-r2-upload-zone]");
    if (!zone || zone.dataset.noDrag === "1") return;
    event.preventDefault();
    void handleZoneFiles(zone, event.dataTransfer?.files);
  }

  document.addEventListener("change", onZoneChange, true);
  document.addEventListener("dragover", onZoneDragOver, true);
  document.addEventListener("drop", onZoneDrop, true);
})();
"""


def _zone_id(key_prefix: str) -> str:
    digest = hashlib.sha1(key_prefix.encode("utf-8")).hexdigest()[:10]
    return f"r2-zone-{digest}"


def _embedded_upload_token(
    key_prefix: str | rx.Var,
    *,
    allowed_extensions: list[str] | None = None,
    content_type: str = "application/octet-stream",
) -> str:
    if not upload_auth_enabled():
        return ""
    if not isinstance(key_prefix, str):
        return ""
    try:
        return issue_upload_token(
            key_prefix,
            allowed_extensions=allowed_extensions,
            content_type=content_type,
        )
    except (ValueError, RuntimeError):
        return ""


def _resolve_accept(
    accept: str,
    allowed_extensions: list[str] | None,
) -> str:
    if allowed_extensions and accept == "*/*":
        return ",".join(allowed_extensions)
    return accept


def _upload_zone_status(*, class_name: str | None = None) -> rx.Component:
    """Status line inside a zone; use with ``upload_zone.root(..., show_status=False)``."""
    return rx.el.p(
        "",
        data_r2_status="1",
        data_r2_status_error="0",
        class_name=class_name or "mt-2 text-xs text-gray-500 data-[r2-status-error=1]:text-red-600",
    )


def _upload_zone_root(
    *children: rx.Component,
    key_prefix: str | rx.Var,
    on_success: rx.EventHandler,
    accept: str = "*/*",
    allowed_extensions: list[str] | None = None,
    content_type: str = "application/octet-stream",
    multiple: bool = False,
    on_error: rx.EventHandler | None = None,
    disabled: bool | rx.Var = False,
    no_click: bool = False,
    no_drag: bool = False,
    no_keyboard: bool = False,
    show_status: bool = True,
    status_class_name: str | None = None,
    class_name: str | None = None,
    **props,
) -> rx.Component:
    """Unstyled upload root; place custom children inside (like ``rx.upload.root``)."""
    del on_error  # reserved for a future release
    prefix_literal = key_prefix if isinstance(key_prefix, str) else str(key_prefix)
    zone_id = _zone_id(prefix_literal)
    bridge_id = f"{zone_id}-bridge"
    file_input_id = f"{zone_id}-file"
    extensions = ",".join(allowed_extensions or [])
    accept_value = _resolve_accept(accept, allowed_extensions)
    upload_token = _embedded_upload_token(
        key_prefix,
        allowed_extensions=allowed_extensions,
        content_type=content_type,
    )

    file_input = rx.el.input(
        id=file_input_id,
        type="file",
        accept=accept_value,
        multiple=multiple,
        disabled=disabled,
        class_name="hidden",
        **({"tab_index": -1} if no_keyboard else {}),
    )

    if no_click:
        trigger: rx.Component = (
            rx.fragment(*children, file_input)
            if children
            else file_input
        )
    elif children:
        trigger = rx.el.label(
            *children,
            file_input,
            class_name="contents cursor-pointer",
        )
    else:
        trigger = rx.el.label(
            file_input,
            class_name="block min-h-[2rem] cursor-pointer",
        )

    status_el = (
        _upload_zone_status(class_name=status_class_name)
        if show_status
        else rx.fragment()
    )

    return rx.el.div(
        rx.el.input(
            id=bridge_id,
            class_name="hidden",
            on_change=on_success,
        ),
        trigger,
        status_el,
        id=zone_id,
        data_r2_upload_zone="1",
        data_key_prefix=key_prefix,
        data_bridge_id=bridge_id,
        data_content_type=content_type,
        data_allowed_extensions=extensions,
        data_upload_token=upload_token,
        data_no_drag="1" if no_drag else "0",
        class_name=class_name,
        **props,
    )


def _upload_zone_styled(
    *,
    key_prefix: str | rx.Var,
    on_success: rx.EventHandler,
    accept: str = "*/*",
    allowed_extensions: list[str] | None = None,
    content_type: str = "application/octet-stream",
    multiple: bool = False,
    label: str = "拖放或点击选择文件",
    on_error: rx.EventHandler | None = None,
    disabled: bool | rx.Var = False,
    class_name: str | None = None,
) -> rx.Component:
    """Styled upload zone preset built on :func:`upload_zone.root`."""
    return _upload_zone_root(
        rx.icon("upload", class_name="mx-auto h-8 w-8 text-violet-500"),
        rx.el.p(label, class_name="mt-3 text-sm font-medium text-gray-800"),
        rx.el.span(
            "选择文件",
            class_name="mt-3 inline-block rounded-lg border border-violet-200 bg-white px-4 py-2 text-xs text-violet-600 hover:bg-violet-50",
        ),
        key_prefix=key_prefix,
        on_success=on_success,
        accept=accept,
        allowed_extensions=allowed_extensions,
        content_type=content_type,
        multiple=multiple,
        on_error=on_error,
        disabled=disabled,
        class_name=class_name
        or "w-full rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 px-6 py-8 text-center transition hover:border-violet-300 hover:bg-violet-50/40",
    )


class UploadZone:
    """Upload zone namespace: styled preset, unstyled root, and status helper."""

    root = staticmethod(_upload_zone_root)
    status = staticmethod(_upload_zone_status)

    def __call__(self, **kwargs) -> rx.Component:
        return _upload_zone_styled(**kwargs)


upload_zone = UploadZone()
