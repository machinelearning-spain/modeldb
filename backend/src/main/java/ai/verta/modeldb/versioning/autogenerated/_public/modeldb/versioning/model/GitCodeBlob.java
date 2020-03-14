// THIS FILE IS AUTO-GENERATED. DO NOT EDIT
package ai.verta.modeldb.versioning.autogenerated._public.modeldb.versioning.model;

import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

import ai.verta.modeldb.ModelDBException;
import ai.verta.modeldb.versioning.*;
import ai.verta.modeldb.versioning.blob.visitors.Visitor;

public class GitCodeBlob {
    public String Repo;
    public String Hash;
    public String Branch;
    public String Tag;
    public Boolean IsDirty;

    public GitCodeBlob() {
        this.Repo = null;
        this.Hash = null;
        this.Branch = null;
        this.Tag = null;
        this.IsDirty = false;
    }

    public GitCodeBlob setRepo(String value) {
        this.Repo = value;
        return this;
    }
    public GitCodeBlob setHash(String value) {
        this.Hash = value;
        return this;
    }
    public GitCodeBlob setBranch(String value) {
        this.Branch = value;
        return this;
    }
    public GitCodeBlob setTag(String value) {
        this.Tag = value;
        return this;
    }
    public GitCodeBlob setIsDirty(Boolean value) {
        this.IsDirty = value;
        return this;
    }

    static public GitCodeBlob fromProto(ai.verta.modeldb.versioning.GitCodeBlob blob) {
        GitCodeBlob obj = new GitCodeBlob();
        {
            Function<String,String> f = null;
            if (f != null) {
                obj.Repo = f.apply(null);
            }
        }
        {
            Function<String,String> f = null;
            if (f != null) {
                obj.Hash = f.apply(null);
            }
        }
        {
            Function<String,String> f = null;
            if (f != null) {
                obj.Branch = f.apply(null);
            }
        }
        {
            Function<String,String> f = null;
            if (f != null) {
                obj.Tag = f.apply(null);
            }
        }
        {
            Function<Boolean,Boolean> f = null;
            if (f != null) {
                obj.IsDirty = f.apply(null);
            }
        }
        return obj;
    }

    public void preVisitShallow(Visitor visitor) throws ModelDBException {
        visitor.preVisit(this);
    }

    public void preVisitDeep(Visitor visitor) throws ModelDBException {
        this.preVisitShallow(visitor);
        {
            Function<String,Void> f = null;
            if (f != null) {
                f.apply(this.Repo);
            }
        }
        {
            Function<String,Void> f = null;
            if (f != null) {
                f.apply(this.Hash);
            }
        }
        {
            Function<String,Void> f = null;
            if (f != null) {
                f.apply(this.Branch);
            }
        }
        {
            Function<String,Void> f = null;
            if (f != null) {
                f.apply(this.Tag);
            }
        }
        {
            Function<Boolean,Void> f = null;
            if (f != null) {
                f.apply(this.IsDirty);
            }
        }
    }

    public GitCodeBlob postVisitShallow(Visitor visitor) throws ModelDBException {
        return visitor.postVisit(this);
    }

    public GitCodeBlob postVisitDeep(Visitor visitor) throws ModelDBException {
        {
            Function<String,String> f = null;
            if (f != null) {
                this.Repo = f.apply(this.Repo);
            }
        }
        {
            Function<String,String> f = null;
            if (f != null) {
                this.Hash = f.apply(this.Hash);
            }
        }
        {
            Function<String,String> f = null;
            if (f != null) {
                this.Branch = f.apply(this.Branch);
            }
        }
        {
            Function<String,String> f = null;
            if (f != null) {
                this.Tag = f.apply(this.Tag);
            }
        }
        {
            Function<Boolean,Boolean> f = null;
            if (f != null) {
                this.IsDirty = f.apply(this.IsDirty);
            }
        }
        return this.postVisitShallow(visitor);
    }
}