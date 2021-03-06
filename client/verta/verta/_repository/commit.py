# -*- coding: utf-8 -*-

from __future__ import print_function

import collections
import heapq

from .._protos.public.modeldb.versioning import VersioningService_pb2 as _VersioningService

from ..external import six

from .._internal_utils import _utils
from .. import code
from .. import configuration
from .. import dataset
from .. import environment
from . import blob as blob_module
from . import diff as diff_module


class Commit(object):
    """
    Commit within a ModelDB Repository.

    There should not be a need to instantiate this class directly; please use
    :meth:`Repository.get_commit() <verta._repository.Repository.get_commit>`.

    Attributes
    ----------
    id : str or None
        ID of the Commit, or ``None`` if the Commit has not yet been saved.

    """
    def __init__(self, conn, repo, parent_ids=None, id_=None, date=None, branch_name=None):
        self._conn = conn

        self._repo = repo
        self._parent_ids = list(collections.OrderedDict.fromkeys(parent_ids or []))  # remove duplicates while maintaining order

        self.id = id_
        self.date = date
        self.branch_name = branch_name  # TODO: find a way to clear if branch is moved

        self._blobs = dict()  # will be loaded when needed
        self._loaded_from_remote = False

    @property
    def parent(self):
        return self._repo.get_commit(id=self._parent_ids[0]) if self._parent_ids else None

    def _lazy_load_blobs(self):
        if self._loaded_from_remote:
            return

        # until Commits can be created from blob diffs, load in blobs
        if self.id is not None:
            self._update_blobs_from_commit(self.id)
        else:
            for parent_id in self._parent_ids:
                # parents will be read in first-to-last, possibly overwriting previous blobs
                self._update_blobs_from_commit(parent_id)

        self._loaded_from_remote = True

    def __repr__(self):
        self._lazy_load_blobs()

        branch_and_tag = ' '.join((
            "(Branch: {})".format(self.branch_name) if self.branch_name is not None else '',
            # TODO: put tag here
        ))
        if self.id is None:
            header = "unsaved Commit containing:"
        else:
            # TODO: fetch commit message
            header = "Commit {} containing:".format(self.id)
        contents = '\n'.join((
            "{} ({})".format(path, blob.__class__.__name__)
            for path, blob
            in sorted(six.viewitems(self._blobs))
        ))
        if not contents:
            contents = "<no contents>"

        repr_components = filter(None, (branch_and_tag, header, contents))  # skip empty components
        return '\n'.join(repr_components)

    @classmethod
    def _from_id(cls, conn, repo, id_, **kwargs):
        endpoint = "{}://{}/api/v1/modeldb/versioning/repositories/{}/commits/{}".format(
            conn.scheme,
            conn.socket,
            repo.id,
            id_,
        )
        response = _utils.make_request("GET", endpoint, conn)
        _utils.raise_for_http_error(response)

        response_msg = _utils.json_to_proto(response.json(),
                                            _VersioningService.GetCommitRequest.Response)
        commit_msg = response_msg.commit
        return cls(conn, repo, commit_msg.parent_shas, commit_msg.commit_sha, commit_msg.date_created, **kwargs)

    @staticmethod
    def _raise_lookup_error(path):
        e = LookupError("Commit does not contain path \"{}\"".format(path))
        six.raise_from(e, None)

    def _update_blobs_from_commit(self, id_):
        """Fetches commit `id_`'s blobs and stores them as objects in `self._blobs`."""
        endpoint = "{}://{}/api/v1/modeldb/versioning/repositories/{}/commits/{}/blobs".format(
            self._conn.scheme,
            self._conn.socket,
            self._repo.id,
            id_,
        )
        response = _utils.make_request("GET", endpoint, self._conn)
        _utils.raise_for_http_error(response)

        response_msg = _utils.json_to_proto(response.json(),
                                            _VersioningService.ListCommitBlobsRequest.Response)
        self._blobs.update({
            '/'.join(blob_msg.location): blob_msg_to_object(blob_msg.blob)
            for blob_msg
            in response_msg.blobs
        })

    def _become_child(self):
        """
        This method is for when `self` had been saved and is then modified, meaning that
        this commit object has become a child of the commit that had been saved.

        """
        self._lazy_load_blobs()
        self._parent_ids = [self.id]
        self.id = None

    def _to_create_msg(self, commit_message):
        self._lazy_load_blobs()

        msg = _VersioningService.CreateCommitRequest()
        msg.repository_id.repo_id = self._repo.id  # pylint: disable=no-member
        msg.commit.parent_shas.extend(self._parent_ids)  # pylint: disable=no-member
        msg.commit.message = commit_message

        for path, blob in six.viewitems(self._blobs):
            blob_msg = _VersioningService.BlobExpanded()
            blob_msg.location.extend(path_to_location(path))  # pylint: disable=no-member
            # TODO: move typecheck & CopyFrom to root blob base class
            if isinstance(blob, code._Code):
                blob_msg.blob.code.CopyFrom(blob._msg)  # pylint: disable=no-member
            elif isinstance(blob, configuration._Configuration):
                blob_msg.blob.config.CopyFrom(blob._msg)  # pylint: disable=no-member
            elif isinstance(blob, dataset._Dataset):
                blob_msg.blob.dataset.CopyFrom(blob._msg)  # pylint: disable=no-member
            elif isinstance(blob, environment._Environment):
                blob_msg.blob.environment.CopyFrom(blob._msg)  # pylint: disable=no-member
            else:
                raise RuntimeError("Commit contains an unexpected item {};"
                                   " please notify the Verta development team".format(type(blob)))
            msg.blobs.append(blob_msg)  # pylint: disable=no-member

        return msg

    def walk(self):
        """
        Generates folder names and blob names in this commit by walking through its folder tree.

        Similar to the Python standard library's ``os.walk()``, the yielded `folder_names` can be
        modified in-place to remove subfolders from upcoming iterations or alter the order in which
        they are to be visited.

        Note that, also similar to ``os.walk()``, `folder_names` and `blob_names` are simply the
        *names* of those entities, and *not* their full paths.

        Yields
        ------
        folder_path : str
            Path to current folder.
        folder_names : list of str
            Names of subfolders in `folder_path`.
        blob_names : list of str
            Names of blobs in `folder_path`.

        """
        if self.id is None:
            raise RuntimeError("Commit must be saved before it can be walked")

        endpoint = "{}://{}/api/v1/modeldb/versioning/repositories/{}/commits/{}/path".format(
            self._conn.scheme,
            self._conn.socket,
            self._repo.id,
            self.id,
        )

        locations = [()]
        while locations:
            location = locations.pop()

            msg = _VersioningService.GetCommitComponentRequest()
            msg.location.extend(location)  # pylint: disable=no-member
            data = _utils.proto_to_json(msg)
            response = _utils.make_request("GET", endpoint, self._conn, params=data)
            _utils.raise_for_http_error(response)

            response_msg = _utils.json_to_proto(response.json(), msg.Response)
            folder_msg = response_msg.folder

            folder_path = '/'.join(location)
            folder_names = list(sorted(element.element_name for element in folder_msg.sub_folders))
            blob_names = list(sorted(element.element_name for element in folder_msg.blobs))
            yield (folder_path, folder_names, blob_names)

            locations.extend(
                location + (folder_name,)
                for folder_name
                in reversed(folder_names)  # maintains order, because locations are popped from end
            )

    def update(self, path, blob):
        """
        Adds `blob` to this Commit at `path`.

        If `path` is already in this Commit, it will be updated to the new `blob`.

        Parameters
        ----------
        path : str
            Location to add `blob` to.
        blob : :class:`~verta._repository.blob.Blob`
            ModelDB versioning blob.

        """
        if not isinstance(blob, blob_module.Blob):
            raise TypeError("unsupported type {}".format(type(blob)))

        self._lazy_load_blobs()

        if self.id is not None:
            self._become_child()

        self._blobs[path] = blob

    def get(self, path):
        """
        Retrieves the blob at `path` from this Commit.

        Parameters
        ----------
        path : str
            Location of a blob.

        Returns
        -------
        blob : :class:`~verta._repository.blob.Blob`
            ModelDB versioning blob.

        Raises
        ------
        LookupError
            If `path` is not in this Commit.

        """
        self._lazy_load_blobs()

        try:
            return self._blobs[path]
        except KeyError:
            self._raise_lookup_error(path)

    def remove(self, path):
        """
        Deletes the blob at `path` from this Commit.

        Parameters
        ----------
        path : str
            Location of a blob.

        Raises
        ------
        LookupError
            If `path` is not in this Commit.

        """
        self._lazy_load_blobs()

        if self.id is not None:
            self._become_child()

        try:
            del self._blobs[path]
        except KeyError:
            self._raise_lookup_error(path)

    def save(self, message):
        """
        Saves this commit to ModelDB.

        Parameters
        ----------
        message : str
            Description of this Commit.

        """
        msg = self._to_create_msg(commit_message=message)
        self._save(msg)

    def _save(self, proto_message):
        data = _utils.proto_to_json(proto_message)
        endpoint = "{}://{}/api/v1/modeldb/versioning/repositories/{}/commits".format(
            self._conn.scheme,
            self._conn.socket,
            self._repo.id,
        )
        response = _utils.make_request("POST", endpoint, self._conn, json=data)
        _utils.raise_for_http_error(response)

        response_msg = _utils.json_to_proto(response.json(), proto_message.Response)
        new_commit = self._repo.get_commit(id=response_msg.commit.commit_sha)

        if self.branch_name is not None:
            # update branch to child commit
            new_commit.branch(self.branch_name)

        self.__dict__ = new_commit.__dict__

    def tag(self, tag):
        """
        Assigns a tag to this Commit.

        Parameters
        ----------
        tag : str
            Tag.

        Raises
        ------
        RuntimeError
            If this Commit has not yet been saved.

        """
        if self.id is None:
            raise RuntimeError("Commit must be saved before it can be tagged")

        data = self.id
        endpoint = "{}://{}/api/v1/modeldb/versioning/repositories/{}/tags/{}".format(
            self._conn.scheme,
            self._conn.socket,
            self._repo.id,
            tag,
        )
        response = _utils.make_request("PUT", endpoint, self._conn, json=data)
        _utils.raise_for_http_error(response)

    def branch(self, branch):
        """
        Assigns a branch to this Commit.

        Parameters
        ----------
        branch : str
            Branch name.

        Raises
        ------
        RuntimeError
            If this Commit has not yet been saved.

        """
        if self.id is None:
            raise RuntimeError("Commit must be saved before it can be attached to a branch")

        data = self.id
        endpoint = "{}://{}/api/v1/modeldb/versioning/repositories/{}/branches/{}".format(
            self._conn.scheme,
            self._conn.socket,
            self._repo.id,
            branch,
        )
        response = _utils.make_request("PUT", endpoint, self._conn, json=data)
        _utils.raise_for_http_error(response)

        self.branch_name = branch

    def diff_from(self, reference=None):
        """
        Returns the diff from `reference` to `self`.

        Parameters
        ----------
        reference : :class:`Commit`, optional
            Commit to be compared to.

        Returns
        -------
        :class:`~verta._repository.diff.Diff`
            Commit diff.

        Raises
        ------
        RuntimeError
            If this Commit or `reference` has not yet been saved, or if they do not belong to the
            same Repository.

        """
        # TODO: check that they belong to the same repo?
        # TODO: check that this commit has been saved
        if reference is None:
            reference_id = self._parent_ids[0]
        elif not isinstance(reference, Commit):
            raise ValueError("reference isn't a Commit")
        elif reference.id is None:
            raise ValueError("reference must be a saved Commit")
        else:
            reference_id = reference.id

        endpoint = "{}://{}/api/v1/modeldb/versioning/repositories/{}/diff?commit_a={}&commit_b={}".format(
            self._conn.scheme,
            self._conn.socket,
            self._repo.id,
            reference_id,
            self.id,
        )
        response = _utils.make_request("GET", endpoint, self._conn)
        _utils.raise_for_http_error(response)

        response_msg = _utils.json_to_proto(response.json(),
                                            _VersioningService.ComputeRepositoryDiffRequest.Response)
        return diff_module.Diff(response_msg.diffs)

    def apply_diff(self, diff, message):
        """
        Applies a diff to this Commit.

        This method creates a new Commit in ModelDB, and assigns a new ID to this object.

        Parameters
        ----------
        diff : :class:`~verta._repository.diff.Diff`
            Commit diff.
        message : str
            Description of the diff.

        Raises
        ------
        RuntimeError
            If this Commit has not yet been saved.

        """
        # TODO: check that this commit has been saved
        msg = _VersioningService.CreateCommitRequest()
        msg.repository_id.repo_id = self._repo.id
        msg.commit.parent_shas.append(self.id)
        msg.commit.message = message
        msg.commit_base = self.id
        msg.diffs.extend(diff._diffs)

        self._save(msg)

    def get_revert_diff(self):
        return self.parent.diff_from(self)

    def revert(self, other=None, message=None):
        """
        Reverts all the Commits beginning with `other` up through this Commit.

        This method creates a new Commit in ModelDB, and assigns a new ID to this object.

        Parameters
        ----------
        other : :class:`Commit`, optional
            Base for the revert. If not provided, this Commit will be reverted.
        message : str, optional
            Description of the revert. If not provided, a default message will be used.

        Raises
        ------
        RuntimeError
            If this Commit or `other` has not yet been saved, or if they do not belong to the
            same Repository.

        """
        # TODO: check that commits have been saved
        # TODO: check same repo
        if other is None:
            other = self
        if message is None:
            message = "Revert {}".format(other.id[:7])

        self.apply_diff(other.get_revert_diff(), message)

    def _to_heap_element(self):
        # Most recent has higher priority
        return (-self.date, self.id, self)  # pylint: disable=invalid-unary-operand-type

    def get_common_parent(self, other):
        # TODO: check other is a Commit
        # TODO: check same repo

        # Keep a set of all parents we see for each side. This doesn't have to be *all* but facilitates implementation
        left_ids = set([self.id])
        right_ids = set([other.id])

        # Keep a heap of all candidate commits to be the common parent, ordered by the date so that we fetch the most recent first
        heap = []
        heapq.heappush(heap, self._to_heap_element())
        heapq.heappush(heap, other._to_heap_element())

        while heap:
            # Get the most recent commit
            _, _, commit = heapq.heappop(heap)

            # If it's in the list for both sides, then it's a parent of both and return
            if commit.id in left_ids and commit.id in right_ids:
                return commit

            # Update the heap with all the current parents
            parent_ids = commit._parent_ids
            for parent_id in parent_ids:
                parent_commit = self._repo.get_commit(id=parent_id)
                heap_element = parent_commit._to_heap_element()
                try:
                    heapq.heappush(heap, heap_element)
                except TypeError:  # already in heap, because comparison between Commits failed
                    pass

            # Update the parent sets based on which side the commit came from
            # We know the commit came from the left if its ID is in the left set. If it was on the right too, then it would be the parent and we would have returned early
            if commit.id in left_ids:
                left_ids.update(parent_ids)
            if commit.id in right_ids:
                right_ids.update(parent_ids)

        # Should never happen, since we have the initial commit
        return None

    def merge(self, other, message=None):
        """
        Merges a branch headed by `other` into this Commit.

        This method creates a new Commit in ModelDB, and assigns a new ID to this object.

        Parameters
        ----------
        other : :class:`Commit`
            Commit to be merged.
        message : str, optional
            Description of the merge. If not provided, a default message will be used.

        Raises
        ------
        RuntimeError
            If this Commit or `other` has not yet been saved, or if they do not belong to the
            same Repository.

        """
        # TODO: check that commits have been saved
        # TODO: check same repo
        if message is None:
            message = "Merge {} into {}".format(
                other.branch_name or other.id[:7],
                self.branch_name or self.id[:7],
            )

        self.apply_diff(other.diff_from(self.get_common_parent(other)), message=message)


def blob_msg_to_object(blob_msg):
    # TODO: make this more concise
    content_type = blob_msg.WhichOneof('content')
    content_subtype = None
    obj = None
    if content_type == 'code':
        content_subtype = blob_msg.code.WhichOneof('content')
        if content_subtype == 'git':
            obj = code.Git()  # TODO: skip obj init, because it requires git
        elif content_subtype == 'notebook':
            obj = code.Notebook()  # TODO: skip obj init, because it requires Jupyter
    elif content_type == 'config':
        obj = configuration.Hyperparameters()
    elif content_type == 'dataset':
        content_subtype = blob_msg.dataset.WhichOneof('content')
        if content_subtype == 's3':
            obj = dataset.S3(paths=[])
        elif content_subtype == 'path':
            obj = dataset.Path(paths=[])
    elif content_type == 'environment':
        content_subtype = blob_msg.environment.WhichOneof('content')
        if content_subtype == 'python':
            obj = environment.Python()
        elif content_subtype == 'docker':
            raise NotImplementedError

    if obj is None:
        if content_subtype is None:
            raise NotImplementedError("found unexpected content type {};"
                                      " please notify the Verta development team".format(content_type))
        else:
            raise NotImplementedError("found unexpected {} type {};"
                                      " please notify the Verta development team".format(content_type, content_subtype))

    obj._msg.CopyFrom(getattr(blob_msg, content_type))
    return obj


def path_to_location(path):
    """Messages take a `repeated string` of path components."""
    if path.startswith('/'):
        # `path` is already meant to be relative to repo root
        path = path[1:]

    return path.split('/')

def location_to_path(location):
    return '/'.join(location)
