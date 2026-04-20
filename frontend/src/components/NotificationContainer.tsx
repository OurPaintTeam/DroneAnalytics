import { useEffect } from "react"
import { useNotificationStore } from "./notificationStore"

export default function NotificationContainer() {
    const notifications = useNotificationStore(s => s.notifications)
    const remove = useNotificationStore(s => s.remove)

    return (
        <div className="fixed top-4 right-4 z-50 space-y-2">
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
    notification: any
    onClose: () => void
}) {
    useEffect(() => {
        const timer = setTimeout(onClose, 4000)
        return () => clearTimeout(timer)
    }, [onClose])

    const color =
        notification.type === "error"
            ? "bg-red-500"
            : notification.type === "success"
                ? "bg-green-500"
                : "bg-blue-500"

    return (
        <div className={`${color} text-white px-4 py-2 rounded shadow-lg`}>
            {notification.message}
        </div>
    )
}