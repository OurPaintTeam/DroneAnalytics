import {useEffect, useState} from "react"
import {useNavigate} from "react-router-dom"

import {fetchLogJsonArray} from "../api/fetchLogs"
import EventSafetyLogFilters from "../components/EventSafetyLogFilters"
import LogPanel, {downloadLogs} from "../components/LogPanel"
import {checkAuth} from "../components/TokenCheck"

interface EventLog {
    timestamp: number
    service: string
    service_id: number
    severity: string
    message: string
}

export default function EventLogPage() {
    const [logs, setLogs] = useState<EventLog[]>([])
    const [searchParams, setSearchParams] = useState(() => new URLSearchParams())
    const navigate = useNavigate()

    useEffect(() => {
        let cancelled = false
        const run = async () => {
            const authorized = await checkAuth()
            if (!authorized) {
                navigate("/login")
                return
            }
            try {
                const data = await fetchLogJsonArray("/log/event", searchParams)
                if (!cancelled) setLogs(data as EventLog[])
            } catch {
                if (!cancelled) console.error("Ошибка загрузки журнала")
            }
        }
        void run()
        return () => {
            cancelled = true
        }
    }, [navigate, searchParams])

    return (
        <LogPanel<EventLog>
            title="Журнал событий"
            logs={logs}
            filters={<EventSafetyLogFilters onApply={setSearchParams} />}
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
            onDownload={(from, to) => downloadLogs("/log/download/event", from, to)}
        />
    )
}
