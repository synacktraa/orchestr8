# DirectoryTracker

> `DirectoryTracker` requires `git` for version control, you can download it from [here](https://git-scm.com/downloads)

This component wraps Git commands to provide simple version control capabilities, including tracking changes, committing modifications, and undoing uncommitted changes. It supports large files through Git LFS when directory size exceeds a configurable limit.

Working with the `DirectoryTracker` class is straightforward:

```python
import orchestr8 as o8

tracker = o8.DirectoryTracker(
    path="path/to/directory", # Directory you want to track
    use_lfs_after_size=200 # Use Git LFS if directory size exceeds 200MB
)

# Check if directory is being tracked
print(tracker.is_tracking)

# Check for changes
print(tracker.has_changes)

# Undo all uncommited changes if needed
tracker.undo()

# Committing changes
tracker.commit("Added new files")

# Commit the changes and delete the .git directory
tracker.delete(commit=True)

# Initialize tracking explicitly
tracker.initialize()
```
