import * as React from "react"
import {useEffect, useRef, useState} from "react"
import {RED} from "../config.ts"
import {BACKEND_URL} from "../config"
import MUIRangePicker from "./DateRangePicker.tsx"

export interface Column<T> {
    key: keyof T
    label: string
    render?: (value: any, row: T) => React.ReactNode
}

export interface LogPanelProps<T> {
    title: string
    logs: T[]
    columns?: Column<T>[]
    onDownload?: (from: Date | null, to: Date | null) => void
}

export const downloadLogs = async (
    urlPath: string,
    fromDate: Date | null,
    toDate: Date | null
) => {
    try {
        const access = localStorage.getItem("access_token")
        if (!access) {
            console.error("❌ access token")
            return
        }

        const params = new URLSearchParams()
        if (fromDate) params.append("from_ts", String(fromDate.getTime()))
        if (toDate) params.append("to_ts", String(toDate.getTime()))

        const url = `${BACKEND_URL}${urlPath}${params.toString() ? `?${params.toString()}` : ""}`

        const res = await fetch(url, {
            method: "GET",
            headers: {Authorization: `Bearer ${access}`},
        })

        if (!res.ok) {
            const text = await res.text()
            console.error("❌ Server response:", text)
            throw new Error("Failed to download logs")
        }

        const blob = await res.blob()
        const downloadUrl = URL.createObjectURL(blob)

        const a = document.createElement("a")
        a.href = downloadUrl
        const contentDisposition = res.headers.get("Content-Disposition")
        let filename = "file.csv"
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?(.+?)"?$/)
            if (match?.[1]) filename = match[1]
        }
        a.download = filename
        a.click()

        URL.revokeObjectURL(downloadUrl)
    } catch (err) {
        console.error("❌ Download failed:", err)
    }
}

export default function LogPanel<T>({title, logs, columns, onDownload}: LogPanelProps<T>) {
    const logsEndRef = useRef<HTMLDivElement>(null)

    const [showPicker, setShowPicker] = useState(false)
    const [dateRange, setDateRange] = useState<[Date | null, Date | null]>([null, null])
    const [startDate, endDate] = dateRange


    useEffect(() => {
        logsEndRef.current?.scrollIntoView({behavior: "smooth"})
    }, [logs])

    const handleDownload = () => {
        if (!onDownload) return
        onDownload(startDate, endDate)
    }

    return (
        <div
            className="h-[calc(100vh-4rem)] flex flex-col overflow-hidden relative font-sans bg-white text-gray-800 pt-6 pb-6">
            <div className="flex-1 flex flex-col mx-6 rounded-xl shadow-2xl relative bg-white overflow-hidden">

                {/* red line */}
                <div className="absolute top-0 left-0 right-0 h-[3px]" style={{backgroundColor: RED}}/>

                {/* header */}
                <div
                    className="px-6 py-2 flex justify-between items-center border-b text-sm font-semibold text-gray-600 relative">
                    <span>{title}</span>

                    {onDownload && (
                        <div className="flex items-center gap-2 relative">
                            <button
                                onClick={() => setShowPicker(prev => !prev)}
                                className="px-3 py-1.5 rounded-md text-sm text-white transition-transform duration-150 ease-in-out
                   hover:scale-105 hover:bg-gray-600 active:scale-95"
                                style={{background: "#e6e6e6"}}
                            >
                                📅
                            </button>

                            <button
                                onClick={handleDownload}
                                className="px-4 py-1.5 rounded-md text-sm font-medium text-white shadow-sm
                   transition-transform duration-150 ease-in-out
                   hover:scale-105 hover:brightness-110 active:scale-95"
                                style={{background: RED}}
                            >
                                Скачать
                            </button>

                            {showPicker && (
                                <div
                                    className="absolute top-full mt-2"
                                    style={{
                                        minWidth: "350px",
                                        left: "40%",
                                        transform: "translateX(calc(-40% - 110px))"
                                    }}
                                >
                                    <MUIRangePicker
                                        from={startDate}
                                        to={endDate}
                                        onChange={(from, to) => setDateRange([from, to])}
                                    />
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* logs / table */}
                <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2 font-mono text-sm text-gray-600">
                    {columns ? (
                        <table className="w-full table-auto border-collapse text-left">
                            <thead>
                            <tr>
                                {columns.map(col => (
                                    <th key={String(col.key)} className="border-b px-2 py-1 font-medium text-gray-700">
                                        {col.label}
                                    </th>
                                ))}
                            </tr>
                            </thead>
                            <tbody>
                            {logs.map((log, i) => (
                                <tr key={i} className="hover:bg-gray-50">
                                    {columns.map(col => (
                                        <td key={String(col.key)} className="px-2 py-1 border-l-2"
                                            style={{borderColor: RED}}>
                                            {col.render ? col.render(log[col.key], log) : String(log[col.key])}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    ) : (

                        logs.map((log, i) => (
                            <div key={i} className="pl-3 border-l-2" style={{borderColor: RED}}>
                                {String(log)}
                            </div>
                        ))
                    )}
                    <div ref={logsEndRef}/>
                </div>
            </div>
        </div>
    )
}