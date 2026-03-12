import {useEffect, useState} from "react"
import {useNavigate} from "react-router-dom"

import {BACKEND_URL} from "../config"
import LogPanel from "../components/LogPanel"
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
                const res = await fetch(`${BACKEND_URL}/log/safety`, {
                    headers: {Authorization: `Bearer ${access}`}
                })
                const data: SecurityLog[] = await res.json()
                setLogs(data)
            } catch {
                console.error("❌ Ошибка подключения")
            }
        }

        init()
    }, [navigate])

    const downloadLogs = () => {
        const blob = new Blob([logs.join("\n")], {type: "text/plain"})
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `security_logs_${new Date().toISOString()}.txt`
        a.click()
        URL.revokeObjectURL(url)
    }

    return (
        <LogPanel<SecurityLog>
            title="Журнал безопасности"
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
            onDownload={downloadLogs}
        />
    )
}