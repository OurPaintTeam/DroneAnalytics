import {useEffect, useRef} from "react"
import {RED} from "../config.ts"
import * as React from "react";

export interface Column<T> {
    key: keyof T
    label: string
    render?: (value: any, row: T) => React.ReactNode
}

export interface LogPanelProps<T> {
    title: string
    logs: T[]
    columns?: Column<T>[]
    onDownload?: () => void
}

export default function LogPanel<T>({title, logs, columns, onDownload}: LogPanelProps<T>) {
    const logsEndRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        logsEndRef.current?.scrollIntoView({behavior: "smooth"})
    }, [logs])

    return (
        <div
            className="h-[calc(100vh-4rem)] flex flex-col overflow-hidden relative font-sans bg-white text-gray-800 pt-6 pb-6">
            <div className="flex-1 flex flex-col mx-6 rounded-xl shadow-2xl relative bg-white overflow-hidden">

                {/* red line */}
                <div className="absolute top-0 left-0 right-0 h-[3px]" style={{backgroundColor: RED}}/>

                {/* header */}
                <div
                    className="px-6 py-2 flex justify-between items-center border-b text-sm font-semibold text-gray-600">
                    <span>{title}</span>

                    {onDownload && (
                        <button
                            onClick={onDownload}
                            className="px-4 py-1.5 rounded-md text-sm font-medium text-white shadow-sm"
                            style={{background: RED}}
                        >
                            Скачать логи
                        </button>
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