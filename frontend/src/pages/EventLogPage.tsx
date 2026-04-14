import {useEffect, useState} from "react"
import {useNavigate} from "react-router-dom"

import {fetchLogJsonArray} from "../api/fetchLogs"
import EventSafetyLogFilters from "../components/EventSafetyLogFilters"
import LogPanel, {downloadLogs} from "../components/LogPanel"
import {buildLogListSearchParams, LOG_PAGE_DEFAULT, type LogPageSize} from "../logPagination"

interface EventLog {
    timestamp: number
    service: string
    service_id: number
    severity: string
    message: string
}

export default function EventLogPage() {
    const [logs, setLogs] = useState<EventLog[]>([])
    const [filterParams, setFilterParams] = useState(() => new URLSearchParams())
    const [page, setPage] = useState(1)
    const [limit, setLimit] = useState<LogPageSize>(LOG_PAGE_DEFAULT)
    const navigate = useNavigate()
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        const run = async () => {
            try {
                const listParams = buildLogListSearchParams(filterParams, page, limit)
                const data = await fetchLogJsonArray("/log/event", listParams)
                if (!cancelled) setLogs(data as EventLog[])
            } catch (e: any) {
                if (cancelled) return
                console.error("Ошибка загрузки журнала:", e)

                setLogs([])
                setError(e?.message || "Сервер недоступен")
            }
        }
        void run()
        return () => {
            cancelled = true
        }
    }, [navigate, filterParams, page, limit])

    return (
        <LogPanel<EventLog>
            title="Журнал событий"
            logs={logs}
            filters={
                <EventSafetyLogFilters
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
                {key: "service", label: "Service"},
                {key: "service_id", label: "ID"},
                {key: "severity", label: "Severity"},
                {key: "message", label: "Message"},
            ]}
            onDownload={() => downloadLogs("/log/download/event", filterParams)}
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
            error={error}
        />
    )
}
