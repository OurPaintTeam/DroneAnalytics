import {isLogDroneType, isLogServiceType, isLogSeverity, SERVICE_ID_MAX, SERVICE_ID_MIN} from "./logConstants"

export function dateToEpochMs(d: Date | null): number | undefined {
    if (!d) return undefined
    const t = d.getTime()
    return Number.isFinite(t) ? t : undefined
}

export type EventSafetyFilterForm = {
    from: Date | null
    to: Date | null
    service: string
    serviceIdRaw: string
    severity: string
}

export function buildEventSafetySearchParams(f: EventSafetyFilterForm): {
    params: URLSearchParams
    error: string | null
} {
    const params = new URLSearchParams()
    const fromTs = dateToEpochMs(f.from)
    const toTs = dateToEpochMs(f.to)
    if (fromTs !== undefined && toTs !== undefined && fromTs > toTs) {
        return {params, error: "Начало периода не может быть позже конца."}
    }
    if (fromTs !== undefined) params.set("from_ts", String(fromTs))
    if (toTs !== undefined) params.set("to_ts", String(toTs))
    if (f.service && isLogServiceType(f.service)) params.set("service", f.service)
    const trimmedId = f.serviceIdRaw.trim()
    if (trimmedId) {
        const n = Number.parseInt(trimmedId, 10)
        if (!Number.isInteger(n) || n < SERVICE_ID_MIN || n > SERVICE_ID_MAX) {
            return {params, error: `ID сервиса: целое число от ${SERVICE_ID_MIN} до ${SERVICE_ID_MAX}.`}
        }
        params.set("service_id", String(n))
    }
    if (f.severity && isLogSeverity(f.severity)) params.set("severity", f.severity)
    return {params, error: null}
}

export type TelemetryFilterForm = {
    from: Date | null
    to: Date | null
    drone: string
    droneIdRaw: string
}

export function buildTelemetrySearchParams(f: TelemetryFilterForm): {
    params: URLSearchParams
    error: string | null
} {
    const params = new URLSearchParams()
    const fromTs = dateToEpochMs(f.from)
    const toTs = dateToEpochMs(f.to)
    if (fromTs !== undefined && toTs !== undefined && fromTs > toTs) {
        return {params, error: "Начало периода не может быть позже конца."}
    }
    if (fromTs !== undefined) params.set("from_ts", String(fromTs))
    if (toTs !== undefined) params.set("to_ts", String(toTs))
    if (f.drone && isLogDroneType(f.drone)) params.set("drone", f.drone)
    const trimmed = f.droneIdRaw.trim()
    if (trimmed) {
        const n = Number.parseInt(trimmed, 10)
        if (!Number.isInteger(n) || n < 1) {
            return {params, error: "ID дрона: целое число ≥ 1."}
        }
        params.set("drone_id", String(n))
    }
    return {params, error: null}
}
