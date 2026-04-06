import * as React from "react"
import {useEffect, useRef, useState} from "react"
import {BACKEND_URL, RED} from "../config"

export interface Column<T> {
    key: keyof T
    label: string
    render?: (value: any, row: T) => React.ReactNode
}

export interface LogPanelProps<T> {
    title: string
    logs: T[]
    columns?: Column<T>[]
    /** Опциональная панель фильтров. */
    filters?: React.ReactNode
    onDownload?: () => void
}

export const downloadLogs = async (
    urlPath: string,
    params?: URLSearchParams
) => {
    try {
        const access = localStorage.getItem("access_token")
        if (!access) {
            console.error("❌ access token")
            return
        }

        const qs = params?.toString() ?? ""
        const url = `${BACKEND_URL}${urlPath}${qs ? `?${qs}` : ""}`

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

export default function LogPanel<T>({title, logs, columns, filters, onDownload}: LogPanelProps<T>) {
    const logsEndRef = useRef<HTMLDivElement>(null)
    const safeLogs = Array.isArray(logs) ? logs : []

    const [showFilters, setShowFilters] = useState(false)


    useEffect(() => {
        logsEndRef.current?.scrollIntoView({behavior: "smooth"})
    }, [safeLogs])

    const handleDownload = () => {
        if (!onDownload) return
        onDownload()
    }

    return (
        <div
            className="relative flex h-[calc(100vh-4rem)] flex-col overflow-hidden bg-white pt-3 pb-3 font-sans text-gray-800 sm:pt-4 sm:pb-4">
            <div className="relative mx-2 flex flex-1 flex-col overflow-hidden rounded-lg bg-white shadow-xl sm:mx-4 sm:rounded-xl md:mx-6">

                {/* red line */}
                <div className="absolute top-0 left-0 right-0 h-[3px]" style={{backgroundColor: RED}}/>

                {/* header */}
                <div
                    className="relative flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2 text-sm font-semibold text-gray-600 sm:px-4 md:px-6">
                    <div className="flex items-center gap-2 sm:gap-3">
                        <span>{title}</span>
                    </div>

                    <div className="relative flex items-center gap-2">
                        {filters ? (
                            <div className="flex items-center">
                                <button
                                    type="button"
                                    onClick={() => setShowFilters(prev => !prev)}
                                    className="inline-flex items-center gap-1.5 rounded-md border border-[#d8dce6] bg-[#fbfcff] px-2.5 py-1.5 text-xs font-semibold uppercase tracking-[0.04em] text-slate-700 transition hover:-translate-y-[1px] hover:border-[#c2c9d8] hover:bg-white"
                                >
                                    {showFilters ? "Скрыть фильтры" : "Показать фильтры"}
                                    <span className="inline-block text-[10px] leading-none transition-transform duration-300" aria-hidden>
                                        {showFilters ? "▲" : "▼"}
                                    </span>
                                </button>
                            </div>
                        ) : null}

                        {filters && onDownload ? <div className="h-6 w-px bg-[#e6e9f1]"/> : null}

                        {onDownload && (
                            <div className="flex items-center gap-1.5 sm:gap-2">
                                <button
                                    onClick={handleDownload}
                                    className="rounded-md border px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:brightness-110 sm:px-4 sm:text-sm"
                                    style={{background: "linear-gradient(135deg, #9F2D20 0%, #7f2419 100%)", borderColor: "#7f2419"}}
                                >
                                    Скачать
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {filters ? (
                    <div className="border-b border-[#ebeef5] bg-white">
                        <div className={`grid transition-all duration-300 ease-out ${showFilters ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"}`}>
                            <div className="overflow-hidden">
                                <div className={`px-3 pt-2 pb-2.5 sm:px-4 md:px-6 transition-transform duration-300 ${showFilters ? "translate-y-0" : "-translate-y-1"}`}>
                                    {filters}
                                </div>
                            </div>
                        </div>
                    </div>
                ) : null}

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
                            {safeLogs.map((log, i) => (
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
                        safeLogs.map((log, i) => (
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