import { create } from "zustand"

export type NotificationType = "success" | "error" | "info"

export interface Notification {
    id: string
    type: NotificationType
    message: string
}

interface NotificationState {
    notifications: Notification[]
    add: (type: NotificationType, message: string) => void
    remove: (id: string) => void
}

export const useNotificationStore = create<NotificationState>((set) => ({
    notifications: [],

    add: (type, message) =>
        set((state) => ({
            notifications: [
                ...state.notifications,
                {
                    id: crypto.randomUUID(),
                    type,
                    message
                }
            ]
        })),

    remove: (id) =>
        set((state) => ({
            notifications: state.notifications.filter(n => n.id !== id)
        }))
}))