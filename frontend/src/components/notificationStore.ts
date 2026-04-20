import { create } from "zustand"

export type NotificationType = "success" | "error" | "info"

export interface Notification {
    id: number
    type: NotificationType
    message: string
}

interface NotificationState {
    notifications: Notification[]
    add: (type: NotificationType, message: string) => void
    remove: (id: number) => void
}

export const useNotificationStore = create<NotificationState>((set) => ({
    notifications: [],

    add: (type, message) =>
        set((state) => ({
            notifications: [
                ...state.notifications,
                { id: Date.now(), type, message }
            ]
        })),

    remove: (id) =>
        set((state) => ({
            notifications: state.notifications.filter(n => n.id !== id)
        }))
}))