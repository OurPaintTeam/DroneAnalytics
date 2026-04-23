/** Значения совпадают с backend/app/models.py и docs/api.yaml — только whitelist в query. */

export const LOG_SERVICE_TYPES = [
    "aggregator",
    "agriculture",
    "delivery",
    "dronePort",
    "GCS",
    "Gazebo",
    "infopanel",
    "inspector",
    "insurance",
    "operator",
    "OrAT_drones",
    "queen",
    "registry",
    "regulator",
    "SITL",
] as const

export type LogServiceType = (typeof LOG_SERVICE_TYPES)[number]

export const LOG_SEVERITIES = [
    "debug",
    "info",
    "notice",
    "warning",
    "error",
    "critical",
    "alert",
    "emergency",
] as const

export type LogSeverity = (typeof LOG_SEVERITIES)[number]

export const LOG_DRONE_TYPES = ["delivery", "queen", "inspector", "agriculture"] as const

export type LogDroneType = (typeof LOG_DRONE_TYPES)[number]

const SERVICE_SET = new Set<string>(LOG_SERVICE_TYPES)
const SEVERITY_SET = new Set<string>(LOG_SEVERITIES)
const DRONE_SET = new Set<string>(LOG_DRONE_TYPES)

export function isLogServiceType(v: string): v is LogServiceType {
    return SERVICE_SET.has(v)
}

export function isLogSeverity(v: string): v is LogSeverity {
    return SEVERITY_SET.has(v)
}

export function isLogDroneType(v: string): v is LogDroneType {
    return DRONE_SET.has(v)
}

/** api.yaml: id 1..1000 */
export const SERVICE_ID_MIN = 1
export const SERVICE_ID_MAX = 1000
