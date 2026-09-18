export function forceArray<T>(data: T | T[] | null | undefined): T[] {
	if (data === null || data === undefined) {
		return []
	} else if (Object.prototype.toString.call(data) === '[object Arguments]') {
		return Array.prototype.slice.call(data)
	} else if (!Array.isArray(data)) {
		return [data] as T[]
	}
	return data as T[]
}

export function getItemsByIndexes<T>(items: T[], indexes: number[]): T[] {
	return (indexes || []).map(index => items[index]).filter(item => item)
}
