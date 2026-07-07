export interface MetadataFilterState {
  department: string;
  category: string;
  author: string;
  source_type: string;
  tags: string;
}

export const emptyMetadataFilters: MetadataFilterState = {
  department: '',
  category: '',
  author: '',
  source_type: '',
  tags: '',
};

export const buildQueryFilters = (filters: MetadataFilterState) => {
  const tags = filters.tags
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);

  const payload = {
    department: filters.department.trim() || undefined,
    category: filters.category.trim() || undefined,
    author: filters.author.trim() || undefined,
    source_type: filters.source_type || undefined,
    tags,
  };

  const hasFilters = Boolean(
    payload.department ||
    payload.category ||
    payload.author ||
    payload.source_type ||
    payload.tags.length > 0
  );

  return hasFilters ? payload : null;
};
