import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined"
import {useCallback, useEffect, useMemo, useState} from "react"
import {useNavigate} from "react-router-dom"

import {BACKEND_URL, RED} from "../config"
import {checkBackend} from "../api/fetchLogs"
import {LOG_DRONE_TYPES, LOG_SERVICE_TYPES, type LogServiceType} from "../logConstants"
import {ApiError, ApiErrorCode, handleApiError, handleApiErrorBackend, handleAuthError} from "../components/notify"

const ACTIVITY_WINDOW_MS = 24 * 60 * 60 * 1000
const ACTIVITY_LIMIT = 1

type ActivitySource = "event" | "safety" | "telemetry"

interface ActivityLog {
    timestamp?: unknown
}

interface ActivityRow {
    service: LogServiceType
    lastSeen: number | null
    sources: ActivitySource[]
}

const droneServices = new Set<string>(LOG_DRONE_TYPES)

const sourceLabels: Record<ActivitySource, string> = {
    event: "события",
    safety: "безопасность",
    telemetry: "телеметрия",
}

function pluralRu(value: number, one: string, few: string, many: string): string {
    const mod10 = value % 10
    const mod100 = value % 100

    if (mod10 === 1 && mod100 !== 11) return one
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
    return many
}

function formatDateTime(timestamp: number | null): string {
    if (timestamp === null) return "Логов за период нет"
    return new Date(timestamp).toLocaleString()
}

function formatRelative(timestamp: number | null): string {
    if (timestamp === null) return "нет подтверждённого лога"

    const diff = Math.max(0, Date.now() - timestamp)
    const minutes = Math.floor(diff / (60 * 1000))

    if (minutes < 1) return "меньше минуты назад"
    if (minutes < 60) return `${minutes} ${pluralRu(minutes, "минуту", "минуты", "минут")} назад`

    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours} ${pluralRu(hours, "час", "часа", "часов")} назад`

    const days = Math.floor(hours / 24)
    return `${days} ${pluralRu(days, "день", "дня", "дней")} назад`
}

function buildActivityParams(fromTs: number, toTs: number, key: "service" | "drone", value: string) {
    const params = new URLSearchParams()
    params.set("from_ts", String(fromTs))
    params.set("to_ts", String(toTs))
    params.set("limit", String(ACTIVITY_LIMIT))
    params.set("page", "1")
    params.set(key, value)
    return params
}

function mapStatus(status: number): ApiErrorCode {
    switch (status) {
        case 401:
            return ApiErrorCode.UNAUTHORIZED
        case 403:
            return ApiErrorCode.FORBIDDEN
        case 404:
            return ApiErrorCode.NOT_FOUND
        case 500:
            return ApiErrorCode.SERVER_ERROR
        default:
            return ApiErrorCode.SERVER_ERROR
    }
}

async function fetchActivityLogs(path: string, params: URLSearchParams, access: string): Promise<ActivityLog[]> {
    let res: Response

    try {
        res = await fetch(`${BACKEND_URL}${path}?${params.toString()}`, {
            headers: {Authorization: `Bearer ${access}`},
        })
    } catch {
        throw new ApiError(ApiErrorCode.NETWORK_ERROR)
    }

    if (!res.ok) {
        throw new ApiError(mapStatus(res.status))
    }

    const data = await res.json()

    if (!Array.isArray(data)) {
        throw new ApiError(ApiErrorCode.INVALID_RESPONSE)
    }

    return data as ActivityLog[]
}

function latestTimestamp(logs: ActivityLog[]): number | null {
    const timestamps = logs
        .map(log => log.timestamp)
        .filter((value): value is number => typeof value === "number" && Number.isFinite(value))

    if (!timestamps.length) return null

    return Math.max(...timestamps)
}

async function fetchServiceActivity(
    service: LogServiceType,
    fromTs: number,
    toTs: number,
    access: string
): Promise<ActivityRow> {
    const requests: Array<Promise<{source: ActivitySource; lastSeen: number | null}>> = [
        fetchActivityLogs("/log/event", buildActivityParams(fromTs, toTs, "service", service), access)
            .then(logs => ({source: "event", lastSeen: latestTimestamp(logs)})),
        fetchActivityLogs("/log/safety", buildActivityParams(fromTs, toTs, "service", service), access)
            .then(logs => ({source: "safety", lastSeen: latestTimestamp(logs)})),
    ]

    if (droneServices.has(service)) {
        requests.push(
            fetchActivityLogs("/log/telemetry", buildActivityParams(fromTs, toTs, "drone", service), access)
                .then(logs => ({source: "telemetry", lastSeen: latestTimestamp(logs)}))
        )
    }

    const results = await Promise.all(requests)
    const timestamps = results
        .map(result => result.lastSeen)
        .filter((value): value is number => value !== null)
    const lastSeen = timestamps.length ? Math.max(...timestamps) : null

    return {
        service,
        lastSeen,
        sources: results
            .filter(result => result.lastSeen !== null)
            .map(result => result.source),
    }
}

export default function GeneralPage() {
    const [rows, setRows] = useState<ActivityRow[]>([])
    const [loading, setLoading] = useState(true)
    const [errorText, setErrorText] = useState<string | null>(null)
    const [updatedAt, setUpdatedAt] = useState<number | null>(null)
    const navigate = useNavigate()

    const loadActivity = useCallback(async () => {
        setLoading(true)
        setErrorText(null)

        try {
            const access = localStorage.getItem("access_token")

            if (!access) {
                throw new ApiError(ApiErrorCode.NO_TOKEN)
            }

            await checkBackend()

            const toTs = Date.now()
            const fromTs = toTs - ACTIVITY_WINDOW_MS
            const data = await Promise.all(
                LOG_SERVICE_TYPES.map(service => fetchServiceActivity(service, fromTs, toTs, access))
            )

            setRows(data)
            setUpdatedAt(Date.now())
        } catch (e) {
            setRows([])
            setErrorText(handleApiErrorBackend(e))
            handleApiError(e)
            handleAuthError(e, navigate)
        } finally {
            setLoading(false)
        }
    }, [navigate])

    useEffect(() => {
        void loadActivity()
    }, [loadActivity])

    const activeCount = useMemo(() => rows.filter(row => row.lastSeen !== null).length, [rows])
    const silentCount = rows.length - activeCount

    return (
        <div className="min-h-[calc(100vh-4rem)] bg-[#f6f7fb] px-3 py-4 text-slate-800 sm:px-4 md:px-6">
            <section className="relative mx-auto flex max-w-7xl flex-col overflow-hidden rounded-xl bg-white shadow-xl">
                <div className="absolute left-0 right-0 top-0 h-[3px]" style={{backgroundColor: RED}}/>

                <header className="flex flex-col gap-4 border-b border-[#ebeef5] px-4 py-4 sm:px-6 md:flex-row md:items-center md:justify-between">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                            Активность
                        </p>
                        <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
                            Активность сервисов
                        </h1>
                        <p className="mt-1 max-w-2xl text-sm text-slate-500">
                            Зелёный статус означает, что сервис отправлял принятый лог события, безопасности или телеметрии за последние 24 часа.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={() => void loadActivity()}
                        disabled={loading}
                        className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-[#d8dce6] bg-[#fbfcff] px-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:-translate-y-[1px] hover:border-[#c2c9d8] hover:bg-white disabled:pointer-events-none disabled:opacity-45"
                    >
                        <RefreshOutlinedIcon fontSize="small"/>
                        Обновить
                    </button>
                </header>

                <div className="grid gap-px border-b border-[#ebeef5] bg-[#ebeef5] sm:grid-cols-3">
                    <div className="bg-white px-4 py-3 sm:px-6">
                        <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-400">Активны</p>
                        <p className="mt-1 text-2xl font-bold tabular-nums text-emerald-600">{activeCount}</p>
                    </div>
                    <div className="bg-white px-4 py-3 sm:px-6">
                        <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-400">Без свежих логов</p>
                        <p className="mt-1 text-2xl font-bold tabular-nums text-slate-500">{silentCount}</p>
                    </div>
                    <div className="bg-white px-4 py-3 sm:px-6">
                        <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-400">Проверено</p>
                        <p className="mt-1 text-sm font-semibold text-slate-700">
                            {updatedAt ? new Date(updatedAt).toLocaleString() : "Ожидание данных"}
                        </p>
                    </div>
                </div>

                <div className="overflow-x-auto px-4 py-4 sm:px-6">
                    <table className="w-full min-w-[760px] border-collapse text-left text-sm">
                        <thead>
                        <tr className="border-b border-[#ebeef5] text-xs font-semibold uppercase tracking-[0.08em] text-slate-400">
                            <th className="px-2 py-3">Сервис</th>
                            <th className="px-2 py-3">Статус</th>
                            <th className="px-2 py-3">Последний лог</th>
                            <th className="px-2 py-3">Источник</th>
                            <th className="px-2 py-3">Давность</th>
                        </tr>
                        </thead>
                        <tbody>
                        {loading ? (
                            <tr>
                                <td className="px-2 py-8 text-center text-slate-500" colSpan={5}>
                                    Загружаем активность...
                                </td>
                            </tr>
                        ) : errorText ? (
                            <tr>
                                <td className="px-2 py-8 text-center text-slate-500" colSpan={5}>
                                    {errorText}
                                </td>
                            </tr>
                        ) : (
                            rows.map(row => {
                                const isActive = row.lastSeen !== null

                                return (
                                    <tr key={row.service} className="border-b border-[#f0f2f7] transition hover:bg-[#fbfcff]">
                                        <td className="px-2 py-3 font-mono text-sm font-semibold text-slate-800">
                                            {row.service}
                                        </td>
                                        <td className="px-2 py-3">
                                            <span className={`inline-flex items-center gap-2 text-sm font-semibold ${isActive ? "text-emerald-700" : "text-slate-500"}`}>
                                                <span
                                                    className={`h-2.5 w-2.5 rounded-full ${isActive ? "bg-emerald-500 shadow-[0_0_0_4px_rgba(16,185,129,0.14)]" : "bg-slate-300"}`}
                                                    aria-hidden
                                                />
                                                {isActive ? "Лог получен" : "Лога нет"}
                                            </span>
                                        </td>
                                        <td className="px-2 py-3 text-slate-600">{formatDateTime(row.lastSeen)}</td>
                                        <td className="px-2 py-3 text-slate-600">
                                            {row.sources.length ? row.sources.map(source => sourceLabels[source]).join(", ") : "нет"}
                                        </td>
                                        <td className="px-2 py-3 text-slate-500">{formatRelative(row.lastSeen)}</td>
                                    </tr>
                                )
                            })
                        )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    )
}
