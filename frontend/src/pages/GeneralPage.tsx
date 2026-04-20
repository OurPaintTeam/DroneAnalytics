import { useState, useMemo } from "react"
import { LOG_SERVICE_TYPES } from "../logConstants.ts"

const getRandomStatus = () => {
    return Math.random() > 0.5 ? "Working" : "Error"
}

const getRandomTime = () => {
    const now = Date.now()
    const randomOffset = Math.floor(Math.random() * 10 * 60 * 1000)
    return new Date(now - randomOffset)
}

const initialCommands = LOG_SERVICE_TYPES.map((service, index) => ({
    id: index,
    name: service,
    status: getRandomStatus(),
    updatedAt: getRandomTime(),
}))

const GeneralPage = () => {
    const [filter, setFilter] = useState<"All" | "Working" | "Error">("All")
    const [commands] = useState(initialCommands)

    const okCount = commands.filter(c => c.status === "Working").length
    const errorCount = commands.filter(c => c.status === "Error").length

    const filteredCommands = useMemo(() => {
        if (filter === "All") return commands
        return commands.filter(cmd => cmd.status === filter)
    }, [commands, filter])

    const btnBase =
        "px-5 py-2 text-sm font-semibold shadow-sm transition"

    return (
        <div className="min-h-screen bg-gray-100 p-6">

            {/* 🎛 Control Panel */}
            <div className="flex justify-center mb-4">

                <div className="flex rounded-md overflow-hidden shadow">

                    {/* OK */}
                    <button
                        onClick={() => setFilter("Working")}
                        className={`${btnBase} ${
                            filter === "Working"
                                ? "bg-green-600 text-white"
                                : "bg-white text-green-600 "
                        }`}
                    >
                        Working {okCount}
                    </button>

                    {/* ALL */}
                    <button
                        onClick={() => setFilter("All")}
                        className={`${btnBase} ${
                            filter === "All"
                                ? "bg-white text-gray-900  "
                                : "bg-white text-gray-600  "
                        }`}
                    >
                        All {commands.length}
                    </button>

                    {/* ERROR */}
                    <button
                        onClick={() => setFilter("Error")}
                        className={`${btnBase} ${
                            filter === "Error"
                                ? "bg-red-600 text-white"
                                : "bg-white text-red-600 "
                        }`}
                    >
                        Error {errorCount}
                    </button>

                </div>
            </div>

            {/* ➖ Разделитель */}
            <div className="h-px bg-gray-300 mb-6" />

            {/* 📦 Список */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {filteredCommands.map((cmd) => (
                    <div
                        key={cmd.id}
                        className={`p-3 rounded-xl shadow-sm border-l-4 
                        ${
                            cmd.status === "Working"
                                ? "bg-green-50 border-green-500"
                                : "bg-red-50 border-red-500"
                        }`}
                    >
                        <h2 className="text-sm font-semibold capitalize">
                            {cmd.name}
                        </h2>

                        <p
                            className={`mt-1 text-xs font-medium 
                            ${
                                cmd.status === "Working"
                                    ? "text-green-600"
                                    : "text-red-600"
                            }`}
                        >
                            {cmd.status === "Working" ? "Working" : "ERROR"}
                        </p>

                        <p className="mt-1 text-[10px] text-gray-500">
                            {cmd.updatedAt.toLocaleTimeString()}
                        </p>
                    </div>
                ))}
            </div>
        </div>
    )
}

export default GeneralPage