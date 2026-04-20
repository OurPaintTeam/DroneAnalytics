import { useEffect } from "react"
import { useNotificationStore, type Notification } from "./notificationStore"

export default function NotificationContainer() {
    const notifications = useNotificationStore(s => s.notifications)
    const remove = useNotificationStore(s => s.remove)

    return (
        <div className="fixed top-16 right-5 z-50 space-y-2">
            {notifications.map((n) => (
                <Toast
                    key={n.id}
                    notification={n}
                    onClose={() => remove(n.id)}
                />
            ))}
        </div>
    )
}

function Toast({
                   notification,
                   onClose
               }: {
    notification: Notification
    onClose: () => void
}) {
    useEffect(() => {
        const timer = setTimeout(onClose, 4000)
        return () => clearTimeout(timer)
    }, [onClose])

    const configMap = {
        error: {
            border: "#9F2D20",
            bg: "bg-white",
            accent: "text-[#9F2D20]",
            icon: "⚠"
        },
        success: {
            border: "#16a34a",
            bg: "bg-white",
            accent: "text-green-600",
            icon: "✔"
        },
        info: {
            border: "#3b82f6",
            bg: "bg-white",
            accent: "text-blue-600",
            icon: "ℹ"
        }
    }[notification.type]

    return (
        <div
            className={`
                relative flex items-start gap-3
                w-80 px-4 py-3
                rounded-xl shadow-lg
                border-l-4
                ${configMap.bg}
                animate-fade-in
            `}
            style={{ borderColor: configMap.border }}
        >
            <div className={`text-lg ${configMap.accent}`}>
                {configMap.icon}
            </div>

            <div className="flex-1 text-sm text-gray-700">
                {notification.message}
            </div>

            <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-700 text-xs"
            >
                ✕
            </button>
        </div>
    )
}