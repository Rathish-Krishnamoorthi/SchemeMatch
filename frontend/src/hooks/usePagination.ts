import { useState } from 'react'

const PAGE_SIZE = 10

export function usePagination<T>(items: readonly T[], pageSize = PAGE_SIZE) {
  const [requestedPage, setRequestedPage] = useState(1)
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize))
  const page = Math.min(requestedPage, pageCount)
  const startIndex = (page - 1) * pageSize

  return {
    items: items.slice(startIndex, startIndex + pageSize),
    page,
    pageCount,
    pageSize,
    totalItems: items.length,
    setPage: (nextPage: number) => {
      setRequestedPage(Math.max(1, Math.min(nextPage, pageCount)))
    },
  }
}
