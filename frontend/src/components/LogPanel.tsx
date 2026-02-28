import {useEffect, useRef} from "react"
import { RED } from "../config.ts"

export interface LogPanelProps {
    title: string
    logs: string[]
    onDownload?: () => void
}

export default function LogPanel({title, logs, onDownload}: LogPanelProps) {
    const logsEndRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        logsEndRef.current?.scrollIntoView({behavior: "smooth"})
    }, [logs])

    return (
        <div
            className="
        h-[calc(100vh-4rem)]
        flex
        flex-col
        overflow-hidden
        relative
        font-sans
        bg-white
        text-gray-800
        pt-6
        pb-6
      "
        >
            <div
                className="
          flex-1
          flex
          flex-col
          mx-6
          rounded-xl
          shadow-2xl
          relative
          bg-white
          overflow-hidden
        "
            >
                {/* red line */}
                <div
                    className="absolute top-0 left-0 right-0 h-[3px]"
                    style={{backgroundColor: RED}}
                />

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

                {/* logs */}
                <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2 font-mono text-sm text-gray-600">
                    {logs.map((log, i) => (
                        <div key={i} className="pl-3 border-l-2" style={{borderColor: RED}}>
                            [{new Date().toLocaleTimeString()}] {log}
                        </div>
                    ))}
                    <div ref={logsEndRef}/>
                </div>
            </div>
        </div>
    )
}