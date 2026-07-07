import React from 'react';
import { emptyMetadataFilters, type MetadataFilterState } from '../metadata';

interface MetadataFiltersProps {
  filters: MetadataFilterState;
  onChange: (filters: MetadataFilterState) => void;
}

export const MetadataFilters: React.FC<MetadataFiltersProps> = ({ filters, onChange }) => {
  const updateFilter = (field: keyof MetadataFilterState, value: string) => {
    onChange({
      ...filters,
      [field]: value,
    });
  };

  return (
    <div className="metadata-filter-panel">
      <div className="metadata-filter-header">
        <h4 className="section-title">Search Filters</h4>
        <button
          type="button"
          className="metadata-clear-button"
          onClick={() => onChange(emptyMetadataFilters)}
        >
          Clear
        </button>
      </div>

      <div className="metadata-grid">
        <input
          className="metadata-input"
          placeholder="Department"
          value={filters.department}
          onChange={(event) => updateFilter('department', event.target.value)}
        />
        <input
          className="metadata-input"
          placeholder="Category"
          value={filters.category}
          onChange={(event) => updateFilter('category', event.target.value)}
        />
        <input
          className="metadata-input"
          placeholder="Author"
          value={filters.author}
          onChange={(event) => updateFilter('author', event.target.value)}
        />
        <select
          className="metadata-input"
          value={filters.source_type}
          onChange={(event) => updateFilter('source_type', event.target.value)}
        >
          <option value="">Any source</option>
          <option value="pdf">PDF</option>
          <option value="docx">Word</option>
          <option value="txt">Text</option>
          <option value="md">Markdown</option>
          <option value="url">Webpage</option>
        </select>
      </div>

      <input
        className="metadata-input"
        placeholder="Tags: leave, benefits"
        value={filters.tags}
        onChange={(event) => updateFilter('tags', event.target.value)}
      />
      <p className="metadata-filter-note">
        Filters match metadata added during indexing.
      </p>
    </div>
  );
};
