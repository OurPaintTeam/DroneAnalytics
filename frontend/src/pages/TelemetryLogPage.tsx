import {useEffect, useState} from "react"
import {useNavigate} from "react-router-dom"

import {fetchLogJsonArray} from "../api/fetchLogs"
import LogPanel, {downloadLogs} from "../components/LogPanel"
import TelemetryLogFilters from "../components/TelemetryLogFilters"
import {buildLogListSearchParams, LOG_PAGE_DEFAULT, type LogPageSize} from "../logPagination"

interface TelemetryLog {
    timestamp: number
    drone: string
    drone_id: number
    battery: number
    pitch: number
    roll: number
    course: number
    latitude: number
    longitude: number
}

export default function TelemetryLogPage() {
    const [logs, setLogs] = useState<TelemetryLog[]>([])
    const [filterParams, setFilterParams] = useState(() => new URLSearchParams())
    const [page, setPage] = useState(1)
    const [limit, setLimit] = useState<LogPageSize>(LOG_PAGE_DEFAULT)
    const navigate = useNavigate()

    useEffect(() => {
        let cancelled = false
        const run = async () => {
            try {
                const listParams = buildLogListSearchParams(filterParams, page, limit)
                const data = await fetchLogJsonArray("/log/telemetry", listParams)
                if (!cancelled) setLogs(data as TelemetryLog[])
            } catch {
                if (!cancelled) console.error("Ошибка загрузки журнала")
            }
        }
        void run()
        return () => {
            cancelled = true
        }
    }, [navigate, filterParams, page, limit])

    return (
        <LogPanel<TelemetryLog>
            title="Телеметрия"
            logs={logs}
            filters={
                <TelemetryLogFilters
                    onApply={p => {
                        setFilterParams(p)
                        setPage(1)
                    }}
                />
            }
            columns={[
                {
                    key: "timestamp",
                    label: "Time",
                    render: (v: number) => new Date(v).toLocaleString(),
                },
                {key: "drone", label: "Drone"},
                {key: "drone_id", label: "ID"},
                {key: "battery", label: "Battery"},
                {key: "pitch", label: "Pitch"},
                {key: "roll", label: "Roll"},
                {key: "course", label: "Course"},
                {key: "latitude", label: "Latitude"},
                {key: "longitude", label: "Longitude"},
            ]}
            onDownload={() => downloadLogs("/log/download/telemetry", filterParams)}
            pagination={{
                page,
                limit,
                canGoNext: logs.length >= limit,
                onPageChange: setPage,
                onLimitChange: l => {
                    setLimit(l)
                    setPage(1)
                },
            }}
        />
    )
}
