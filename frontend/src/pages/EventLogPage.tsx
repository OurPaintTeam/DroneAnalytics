import {useEffect, useState} from "react"
import {useNavigate} from "react-router-dom"

import {BACKEND_URL} from "../config"
import LogPanel, { downloadLogs } from "../components/LogPanel"
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
    const navigate = useNavigate()

    useEffect(() => {
        const init = async () => {
            const authorized = await checkAuth()
            if (!authorized) {
                navigate("/login")
                return
            }

            try {
                const access = localStorage.getItem("access_token")
                const res = await fetch(`${BACKEND_URL}/log/event`, {
                    headers: {Authorization: `Bearer ${access}`}
                })
                const data: EventLog[] = await res.json()
                setLogs(data)
            } catch {
                console.error("❌ Ошибка подключения")
            }
        }

        init()
    }, [navigate])

    return (
        <LogPanel<EventLog>
            title="Журнал событий"
            logs={logs}
            columns={[
                {
                    key: "timestamp",
                    label: "Time",
                    render: (v: number) => new Date(v).toLocaleString()
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