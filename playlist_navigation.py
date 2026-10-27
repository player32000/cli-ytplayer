"""Playlist selection, sequential history, and shuffle navigation."""

import random


class PlaylistNavigation:
    """Track the playing item, selection, playback history, and shuffle order."""

    def __init__(self, track_count: int) -> None:
        self.track_count = track_count
        self.index = 0
        self.selected_index = 0
        self.shuffle_enabled = False
        self.shuffle_remaining: list[int] = []
        self._history = [0]
        self._history_position = 0

    def move_selection(self, distance: int) -> None:
        self.selected_index = min(
            self.track_count - 1,
            max(0, self.selected_index + distance),
        )

    def toggle_shuffle(self) -> None:
        self.shuffle_enabled = not self.shuffle_enabled
        self.shuffle_remaining.clear()
        if self.shuffle_enabled:
            self.shuffle_remaining.extend(
                item for item in range(self.track_count) if item != self.index
            )
            random.shuffle(self.shuffle_remaining)

    def select(self) -> None:
        self.index = self.selected_index
        if self._history_position < len(self._history) - 1:
            self._history = self._history[:self._history_position + 1]
        if self._history[-1] != self.index:
            self._history.append(self.index)
            self._history_position += 1
        self._remove_from_shuffle(self.index)

    def previous(self) -> None:
        if self._history_position > 0:
            self._history_position -= 1
            self.index = self._history[self._history_position]
        self.selected_index = self.index
        self._remove_from_shuffle(self.index)

    def next(self) -> None:
        if self._history_position < len(self._history) - 1:
            self._history_position += 1
            self.index = self._history[self._history_position]
        else:
            if self.shuffle_enabled:
                if not self.shuffle_remaining:
                    self.shuffle_remaining.extend(
                        item for item in range(self.track_count) if item != self.index
                    )
                    random.shuffle(self.shuffle_remaining)
                self.index = (
                    self.shuffle_remaining.pop()
                    if self.shuffle_remaining
                    else self.track_count
                )
            else:
                self.index += 1

            if self.index < self.track_count:
                self._history.append(self.index)
                self._history_position += 1

        self.selected_index = self.index

    def _remove_from_shuffle(self, index: int) -> None:
        if self.shuffle_enabled and index in self.shuffle_remaining:
            self.shuffle_remaining.remove(index)
