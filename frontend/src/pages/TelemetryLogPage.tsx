import {useEffect, useState} from "react"
import {useNavigate} from "react-router-dom"

import {BACKEND_URL} from "../config"
import LogPanel from "../components/LogPanel"
import {checkAuth} from "../components/TokenCheck"

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
                const res = await fetch(`${BACKEND_URL}/log/telemetry`, {
                    headers: {Authorization: `Bearer ${access}`}
                })
                const data = await res.json()
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
        a.download = `telemetry_logs_${new Date().toISOString()}.txt`
        a.click()
        URL.revokeObjectURL(url)
    }

    return (
        <LogPanel<TelemetryLog>
            title="Телеметрия"
            logs={logs}
            columns={[
                {
                    key: "timestamp",
                    label: "Time",
                    render: (v: number) => new Date(v).toLocaleString()
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
            onDownload={downloadLogs}
        />
    )
}