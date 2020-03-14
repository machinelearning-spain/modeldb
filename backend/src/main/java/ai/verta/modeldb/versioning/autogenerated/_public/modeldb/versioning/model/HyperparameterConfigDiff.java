// THIS FILE IS AUTO-GENERATED. DO NOT EDIT
package ai.verta.modeldb.versioning.autogenerated._public.modeldb.versioning.model;

import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

import ai.verta.modeldb.ModelDBException;
import ai.verta.modeldb.versioning.*;
import ai.verta.modeldb.versioning.blob.visitors.Visitor;

public class HyperparameterConfigDiff {
    public List<HyperparameterConfigBlob> A;
    public List<HyperparameterConfigBlob> B;

    public HyperparameterConfigDiff() {
        this.A = null;
        this.B = null;
    }

    public HyperparameterConfigDiff setA(List<HyperparameterConfigBlob> value) {
        this.A = value;
        return this;
    }
    public HyperparameterConfigDiff setB(List<HyperparameterConfigBlob> value) {
        this.B = value;
        return this;
    }

    static public HyperparameterConfigDiff fromProto(ai.verta.modeldb.versioning.HyperparameterConfigDiff blob) {
        HyperparameterConfigDiff obj = new HyperparameterConfigDiff();
        {
            Function<List<HyperparameterConfigBlob>,List<HyperparameterConfigBlob>> f = null;
            if (f != null) {
                obj.A = f.apply(null);
            }
        }
        {
            Function<List<HyperparameterConfigBlob>,List<HyperparameterConfigBlob>> f = null;
            if (f != null) {
                obj.B = f.apply(null);
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
            Function<List<HyperparameterConfigBlob>,Void> f = v -> {v.stream().forEach(s -> s.preVisitDeep(visitor)); return null;};
            if (f != null) {
                f.apply(this.A);
            }
        }
        {
            Function<List<HyperparameterConfigBlob>,Void> f = v -> {v.stream().forEach(s -> s.preVisitDeep(visitor)); return null;};
            if (f != null) {
                f.apply(this.B);
            }
        }
    }

    public HyperparameterConfigDiff postVisitShallow(Visitor visitor) throws ModelDBException {
        return visitor.postVisit(this);
    }

    public HyperparameterConfigDiff postVisitDeep(Visitor visitor) throws ModelDBException {
        {
            Function<List<HyperparameterConfigBlob>,List<HyperparameterConfigBlob>> f = v -> v.stream().map(s -> s.postVisitDeep(visitor)).collect(Collectors.toList());
            if (f != null) {
                this.A = f.apply(this.A);
            }
        }
        {
            Function<List<HyperparameterConfigBlob>,List<HyperparameterConfigBlob>> f = v -> v.stream().map(s -> s.postVisitDeep(visitor)).collect(Collectors.toList());
            if (f != null) {
                this.B = f.apply(this.B);
            }
        }
        return this.postVisitShallow(visitor);
    }
}