import {useEffect, useState} from "react"
import {useNavigate} from "react-router-dom"

import {fetchLogJsonArray} from "../api/fetchLogs"
import LogPanel, {downloadLogs} from "../components/LogPanel"
import TelemetryLogFilters from "../components/TelemetryLogFilters"
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
                const data = await fetchLogJsonArray("/log/telemetry", searchParams)
                if (!cancelled) setLogs(data as TelemetryLog[])
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
        <LogPanel<TelemetryLog>
            title="Телеметрия"
            logs={logs}
            filters={<TelemetryLogFilters onApply={setSearchParams} />}
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
            onDownload={(from, to) => downloadLogs("/log/download/telemetry", from, to)}
        />
    )
}
