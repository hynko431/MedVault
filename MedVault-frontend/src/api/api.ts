import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_BASE_URL } from "./config";

export async function apiRequest(
    endpoint: string,
    method = "GET",
    body?: any
) {
    const token = await AsyncStorage.getItem("token");

    const headers: any = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.message);
    return data;
}
