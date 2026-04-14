import {useEffect, useState} from "react"
import {useNavigate} from "react-router-dom"

import {fetchLogJsonArray} from "../api/fetchLogs"
import EventSafetyLogFilters from "../components/EventSafetyLogFilters"
import LogPanel, {downloadLogs} from "../components/LogPanel"
import {buildLogListSearchParams, LOG_PAGE_DEFAULT, type LogPageSize} from "../logPagination"

interface SecurityLog {
    timestamp: number
    service: string
    service_id: number
    severity: string
    message: string
}

export default function SecurityLogPage() {
    const [logs, setLogs] = useState<SecurityLog[]>([])
    const [filterParams, setFilterParams] = useState(() => new URLSearchParams())
    const [page, setPage] = useState(1)
    const [limit, setLimit] = useState<LogPageSize>(LOG_PAGE_DEFAULT)
    const navigate = useNavigate()

    useEffect(() => {
        let cancelled = false
        const run = async () => {
            try {
                const listParams = buildLogListSearchParams(filterParams, page, limit)
                const data = await fetchLogJsonArray("/log/safety", listParams)
                if (!cancelled) setLogs(data as SecurityLog[])
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
        <LogPanel<SecurityLog>
            title="Журнал безопасности"
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
            onDownload={() => downloadLogs("/log/download/safety", filterParams)}
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
