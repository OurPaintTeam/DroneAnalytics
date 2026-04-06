import {useEffect, useState} from "react"
import {useNavigate} from "react-router-dom"

import {fetchLogJsonArray} from "../api/fetchLogs"
import EventSafetyLogFilters from "../components/EventSafetyLogFilters"
import LogPanel, {downloadLogs} from "../components/LogPanel"
import {checkAuth} from "../components/TokenCheck"

interface SecurityLog {
    timestamp: number
    service: string
    service_id: number
    severity: string
    message: string
}

export default function SecurityLogPage() {
    const [logs, setLogs] = useState<SecurityLog[]>([])
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
                const data = await fetchLogJsonArray("/log/safety", searchParams)
                if (!cancelled) setLogs(data as SecurityLog[])
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
        <LogPanel<SecurityLog>
            title="Журнал безопасности"
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
            onDownload={() => downloadLogs("/log/download/safety", searchParams)}
        />
    )
}
