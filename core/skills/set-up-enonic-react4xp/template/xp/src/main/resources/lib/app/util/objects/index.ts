export function isEmpty(obj: unknown): boolean {
	let result: boolean
	let typeofObj: string, stringifyObj: string
	const objAsRecord = obj as Record<string, unknown>
	if ((typeofObj = typeof obj) === 'undefined' || obj === null || obj === '') {
		result = true
	} else if (Object.prototype.toString.call(obj) === '[object Date]' && !isNaN(obj as number)) {
		result = false
	} else if (typeofObj === 'string' || objAsRecord.constructor === String || (Array.isArray(obj) && obj.length > 0)) {
		result = false
	} else if (typeofObj === 'boolean' || (typeofObj === 'number' && !isNaN(obj as number)) || (typeof objAsRecord.length === 'number' && (objAsRecord.length as number) > 0)) {
		result = false
	} else if (objAsRecord.blank || objAsRecord.empty || String(obj) === 'undefined' || String(obj) === 'null' || (stringifyObj = JSON.stringify(obj)) === '{}' || stringifyObj === '[]') {
		result = true
	} else {
		const objectCopy = { ...(obj as object) }
		result = Object.keys(objectCopy).length === 0 && (objAsRecord.constructor === Object)
	}
	return result
}

export function JSONParse<T = unknown>(obj: string): T | null {
	try {
		return JSON.parse(obj)
	} catch (err) {
		return null
	}
}
