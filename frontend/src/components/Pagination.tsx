export function Pagination({
  page,
  pageCount,
  pageSize,
  totalItems,
  onPageChange,
}: {
  page: number
  pageCount: number
  pageSize: number
  totalItems: number
  onPageChange: (page: number) => void
}) {
  if (totalItems <= pageSize) return null

  const firstItem = (page - 1) * pageSize + 1
  const lastItem = Math.min(page * pageSize, totalItems)

  return (
    <nav className="pagination" aria-label="List pages">
      <span className="pagination-summary" aria-live="polite">
        Showing {firstItem}–{lastItem} of {totalItems}
      </span>
      <div className="pagination-controls">
        <button type="button" onClick={() => onPageChange(page - 1)} disabled={page === 1}>
          Previous
        </button>
        <span aria-current="page">Page {page} of {pageCount}</span>
        <button type="button" onClick={() => onPageChange(page + 1)} disabled={page === pageCount}>
          Next
        </button>
      </div>
    </nav>
  )
}
