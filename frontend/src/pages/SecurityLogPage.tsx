import {useEffect, useState} from "react"
import {BACKEND_URL} from "../config"
import LogPanel from "../components/LogPanel"

export default function SecurityLogPage() {
    const [logs, setLogs] = useState<string[]>([
        "Инициализация системы...",
        "Подключение к backend...",
    ])

    useEffect(() => {
        fetch(`${BACKEND_URL}`)
            .then(r => r.json())
            .then(d => setLogs(p => [...p, `Backend: ${d.message}`]))
            .catch(() => setLogs(p => [...p, "❌ Ошибка подключения к backend"]))
    }, [])

    const downloadLogs = () => {
        const blob = new Blob([logs.join("\n")], {type: "text/plain"})
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `event_logs_${new Date().toISOString()}.txt`
        a.click()
        URL.revokeObjectURL(url)
    }

    return (
        <LogPanel
            title="Журнал безопасности"
            logs={logs}
            onDownload={downloadLogs}
        />
    )
}