/**
 * Utility functions for handling media URLs from the backend API
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Converts a relative or absolute URL to a full API URL
 * @param url - The URL to convert (can be relative or absolute)
 * @returns Full URL with API base URL prepended if needed
 */
export function getImageUrl(url: string): string {
    if (!url) return '';

    // Already a full URL
    if (url.startsWith('http://') || url.startsWith('https://')) {
        return url;
    }

    // Relative URLs - prepend API base URL
    if (url.startsWith('/media/')) {
        return `${API_BASE_URL}${url}`;
    }

    if (url.startsWith('media/')) {
        return `${API_BASE_URL}/${url}`;
    }

    if (url.startsWith('/')) {
        return `${API_BASE_URL}${url}`;
    }

    // Default case
    return `${API_BASE_URL}/${url}`;
}

/**
 * Gets the API base URL
 * @returns The configured API base URL
 */
export function getApiBaseUrl(): string {
    return API_BASE_URL;
}
